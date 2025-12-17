from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
from json import JSONDecodeError
import time
import re

from app.database import Base, check_db_connection
from app.models import TravelPlan, Location
from app.routers import travel_plans, locations

app = FastAPI(
    title="Travel Planner API (Sharded)",
    description="Travel planner with 16 database shards across 4 PostgreSQL instances",
    version="2.0.0"
)

# Include routers
app.include_router(travel_plans.router)
app.include_router(locations.router)


# === Exception Handlers ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    if isinstance(exc.detail, dict):
        if "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
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
    from app.database import SESSION_MAKERS

    shard_status = {}
    all_healthy = True

    for shard_key, session_maker in SESSION_MAKERS.items():
        try:
            db = session_maker()
            start_time = time.time()
            db.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000
            db.close()

            shard_status[f"shard_{shard_key}"] = {
                "status": "healthy",
                "responseTime": round(response_time, 2)
            }
        except Exception as e:
            all_healthy = False
            shard_status[f"shard_{shard_key}"] = {
                "status": "unhealthy",
                "error": str(e)
            }

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "shards": shard_status
    }


@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Starting Travel Planner API (Sharded)...")

    if check_db_connection():
        print("✓ All shard connections successful")
    else:
        print("✗ Some shard connections failed")

    print("=" * 50)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4567)