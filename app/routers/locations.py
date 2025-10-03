from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/api/locations",
    tags=["Locations"]
)

@router.post("/api/travel-plans/{plan_id}/locations",
             response_model=schemas.LocationBase,
             status_code=status.HTTP_201_CREATED)
def create_location(
    plan_id: UUID,
    location: schemas.CreateLocationRequest,  # Тепер містить plan_version
    db: Session = Depends(get_db)
):
    return crud.add_location(db, plan_id, location)

@router.put("/{location_id}",
            response_model=schemas.LocationBase)
def update_location(
    location_id: UUID,
    location: schemas.UpdateLocationRequest,  # Тепер містить plan_version
    db: Session = Depends(get_db)
):
    return crud.update_location(db, location_id, location)


@router.delete("/{location_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: UUID,
    plan_version: int = Query(..., ge=1),  # Додаємо query параметр
    db: Session = Depends(get_db)
):
    crud.delete_location(db, location_id, plan_version)