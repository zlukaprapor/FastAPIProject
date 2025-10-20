from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/api/locations",
    tags=["Locations"]
)


@router.put("/{location_id}",
            response_model=schemas.LocationBase)
def update_location(
    location_id: UUID,
    location: schemas.UpdateLocationRequest,
    db: Session = Depends(get_db)
):
    """Update a location with optimistic locking"""
    return crud.update_location(db, location_id, location)


@router.delete("/{location_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: UUID,
    plan_version: int = Query(..., ge=1),
    db: Session = Depends(get_db)
):
    """Delete a location with version check"""
    crud.delete_location(db, location_id, plan_version)