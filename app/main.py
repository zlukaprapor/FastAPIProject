from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
from json import JSONDecodeError
import time
import re

# ВАЖЛИВО: Імпортуємо database та Base ПЕРЕД створенням app
from app.database import engine, get_db, Base

# КРИТИЧНО: Імпортуємо моделі ПЕРЕД створенням таблиць
from app.models import TravelPlan, Location

# Імпортуємо роутери
from app.routers import travel_plans, locations

app = FastAPI(
    title="Travel Planner API",
    description="Simple REST API for planning travel itineraries with locations",
    version="1.0.0"
)

# Створюємо таблиці після імпорту всіх моделей
print("Creating database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {e}")
    raise

# Include routers
app.include_router(travel_plans.router)
app.include_router(locations.router)


# === Exception Handlers ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Уніфікуємо всі HTTPException під формат з полем error"""
    if isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    if isinstance(exc.detail, dict):
        # Якщо у словнику вже є error – віддаємо як є
        if "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        # Інакше обгортаємо
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail)}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]

        if "uuid" in msg.lower() or error.get("type") == "uuid_parsing":
            errors.append("Invalid UUID format")
        else:
            errors.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation error",
            "details": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    error_message = str(exc.orig)
    details = []

    if "check_title_not_empty" in error_message or "check_name_not_empty" in error_message:
        details.append("Title/Name cannot be empty or contain only whitespace")
    elif "check_currency_length" in error_message:
        details.append("Currency must be exactly 3 characters")
    elif "check_dates" in error_message:
        details.append("End date must be after or equal to start date")
    elif "check_location_dates" in error_message:
        details.append("Departure date must be after or equal to arrival date")
    elif "check_coordinates_lat" in error_message:
        details.append("Latitude must be between -90 and 90")
    elif "check_coordinates_lng" in error_message:
        details.append("Longitude must be between -180 and 180")
    elif "check_budget" in error_message or "check_location_budget" in error_message:
        details.append("Budget must be greater than or equal to 0")
    elif "check_visit_order_positive" in error_message:
        details.append("Visit order must be greater than 0")
    elif "unique_plan_order" in error_message:
        match = re.search(r'Key \(travel_plan_id, visit_order\)=\([^,]+, (\d+)\)', error_message)
        order = match.group(1) if match else "specified"
        details.append(f"Visit order {order} is already taken for this travel plan")
    elif "foreign key constraint" in error_message.lower():
        details.append("Referenced travel plan does not exist")
    else:
        details.append("Database constraint violation")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Constraint violation",
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)

    if "json" in error_msg.lower() or isinstance(exc, (JSONDecodeError, ValueError)):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid JSON",
                "details": ["Request body contains malformed JSON"],
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# === Service Endpoints ===

@app.get("/health")
async def health_check():
    from sqlalchemy import text
    try:
        db = next(get_db())
        start_time = time.time()
        db.execute(text("SELECT 1"))
        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "healthy",
                "responseTime": round(response_time, 2)
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": {
                    "status": "unhealthy",
                    "error": str(e)
                }
            }
        )


@app.on_event("startup")
async def startup_event():
    from sqlalchemy import text
    print("=" * 50)
    print("Starting Travel Planner API...")
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        print("✓ Database connection successful")

        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"✓ Tables in database: {tables}")

        triggers_result = db.execute(text("""
            SELECT trigger_name 
            FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
            ORDER BY trigger_name
        """))
        triggers = [row[0] for row in triggers_result]
        if triggers:
            print(f"✓ Triggers in database: {triggers}")

        db.close()

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise
    print("=" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
