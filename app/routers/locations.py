from fastapi import APIRouter, status, Query
from uuid import UUID
from app import schemas, crud, models
from app.database import get_all_dbs

router = APIRouter(
    prefix="/api/locations",
    tags=["Locations"]
)


def find_location_shard(location_id: UUID):
    """Знаходить шард, де знаходиться локація"""
    for db in get_all_dbs():
        location = db.query(models.Location).filter(models.Location.id == location_id).first()
        if location:
            return db, location
    return None, None


@router.put("/{location_id}", response_model=schemas.LocationBase)
def update_location(location_id: UUID, location: schemas.UpdateLocationRequest):
    """Оновлює локацію (шукає по всіх шардах)"""
    db, existing = find_location_shard(location_id)
    if not db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Location not found")

    return crud.update_location(db, location_id, location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: UUID, plan_version: int = Query(..., ge=1)):
    """Видаляє локацію (шукає по всіх шардах)"""
    db, existing = find_location_shard(location_id)
    if not db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Location not found")

    crud.delete_location(db, location_id, plan_version)