from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/api/locations",
    tags=["Locations"]
)


@router.put("/{location_id}", response_model=schemas.LocationBase)
def update_location(
    location_id: UUID,
    location_data: schemas.UpdateLocationRequest,
    db: Session = Depends(get_db)
):
    """Update a location"""
    return crud.update_location(db, location_id, location_data)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: UUID, db: Session = Depends(get_db)):
    """Delete a location"""
    crud.delete_location(db, location_id)