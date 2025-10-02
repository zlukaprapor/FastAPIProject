from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app import schemas, crud

router = APIRouter(
    prefix="/api/travel-plans",
    tags=["Travel Plans"]
)


@router.get("", response_model=List[schemas.TravelPlanSummary])
def get_all_travel_plans(db: Session = Depends(get_db)):
    """Get all travel plans with location counts"""
    return crud.get_all_plans(db)


@router.get("/{plan_id}", response_model=schemas.TravelPlanDetails)
def get_travel_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Get a specific travel plan with all its locations"""
    return crud.get_plan_by_id(db, plan_id)


@router.post("", response_model=schemas.TravelPlanBase, status_code=status.HTTP_201_CREATED)
def create_travel_plan(
    plan_data: schemas.CreateTravelPlanRequest,
    db: Session = Depends(get_db)
):
    """Create a new travel plan"""
    return crud.create_plan(db, plan_data)


@router.put("/{plan_id}", response_model=schemas.TravelPlanBase)
def update_travel_plan(
    plan_id: UUID,
    plan_data: schemas.UpdateTravelPlanRequest,
    db: Session = Depends(get_db)
):
    """Update a travel plan with optimistic locking"""
    return crud.update_plan(db, plan_id, plan_data)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Delete a travel plan and all its locations (cascade)"""
    crud.delete_plan(db, plan_id)


@router.post("/{plan_id}/locations", response_model=schemas.LocationBase, status_code=status.HTTP_201_CREATED)
def add_location_to_plan(
    plan_id: UUID,
    location_data: schemas.CreateLocationRequest,
    db: Session = Depends(get_db)
):
    """Add a new location to a travel plan"""
    return crud.add_location(db, plan_id, location_data)