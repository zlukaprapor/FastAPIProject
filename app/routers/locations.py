# app/routers/locations.py
from fastapi import APIRouter, Depends, status, Query
from uuid import UUID

from app.database import get_db
from app import schemas, crud

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.put("/{location_id}", response_model=schemas.LocationBase)
async def update_location(location_id: UUID, location: schemas.UpdateLocationRequest, db=Depends(get_db)):
    return await crud.update_location(db, location_id, location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: UUID, plan_version: int = Query(..., ge=1), db=Depends(get_db)):
    await crud.delete_location(db, location_id, plan_version)
