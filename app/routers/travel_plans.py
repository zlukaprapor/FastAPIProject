# app/routers/travel_plans.py
from fastapi import APIRouter, Depends, status
from typing import List
from uuid import UUID

from app.database import get_db
from app import schemas, crud

router = APIRouter(prefix="/api/travel-plans", tags=["Travel Plans"])


@router.get("", response_model=List[schemas.TravelPlanSummary])
async def get_all_travel_plans(db=Depends(get_db)):
    return await crud.get_all_plans(db)


@router.get("/{plan_id}", response_model=schemas.TravelPlanDetails)
async def get_travel_plan(plan_id: UUID, db=Depends(get_db)):
    return await crud.get_plan_by_id(db, plan_id)


@router.post("", response_model=schemas.TravelPlanBase, status_code=status.HTTP_201_CREATED)
async def create_travel_plan(plan_data: schemas.CreateTravelPlanRequest, db=Depends(get_db)):
    return await crud.create_plan(db, plan_data)


@router.put("/{plan_id}", response_model=schemas.TravelPlanBase)
async def update_travel_plan(plan_id: UUID, plan_data: schemas.UpdateTravelPlanRequest, db=Depends(get_db)):
    return await crud.update_plan(db, plan_id, plan_data)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_travel_plan(plan_id: UUID, db=Depends(get_db)):
    await crud.delete_plan(db, plan_id)


@router.post("/{plan_id}/locations", response_model=schemas.LocationBase, status_code=status.HTTP_201_CREATED)
async def add_location_to_plan(plan_id: UUID, location_data: schemas.CreateLocationRequest, db=Depends(get_db)):
    return await crud.add_location(db, plan_id, location_data)
