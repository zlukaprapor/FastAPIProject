# app/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
from json import JSONDecodeError
import time

from app.routers import travel_plans, locations
from app.database import ping_db, get_db
from app import crud

app = FastAPI(
    title="Travel Planner API",
    description="REST API for planning travel itineraries with locations (MongoDB)",
    version="3.0.0"
)

app.include_router(travel_plans.router)
app.include_router(locations.router)


@app.on_event("startup")
async def startup_event():
    ok = await ping_db()
    if not ok:
        raise RuntimeError("MongoDB connection failed")
    db = get_db()
    await crud.ensure_indexes(db)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, str):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    if isinstance(exc.detail, dict):
        if "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


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
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (JSONDecodeError, ValueError)) and "json" in str(exc).lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid JSON",
                "details": ["Request body contains malformed JSON"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "timestamp": datetime.utcnow().isoformat()},
    )


@app.get("/health")
async def health_check():
    start = time.time()
    ok = await ping_db()
    ms = (time.time() - start) * 1000

    if ok:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {"status": "healthy", "responseTime": round(ms, 2)},
        }

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {"status": "unhealthy"},
        },
    )
