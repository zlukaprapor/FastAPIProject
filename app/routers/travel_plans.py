from fastapi import APIRouter, status
from typing import List
from uuid import UUID, uuid4
from app.database import get_db_for_plan
from app import schemas, crud

router = APIRouter(
    prefix="/api/travel-plans",
    tags=["Travel Plans"]
)


@router.get("", response_model=List[schemas.TravelPlanSummary])
def get_all_travel_plans():
    """Отримує всі плани з усіх шардів"""
    return crud.get_all_plans()


@router.get("/{plan_id}", response_model=schemas.TravelPlanDetails)
def get_travel_plan(plan_id: UUID):
    """Отримує конкретний план зі свого шарду"""
    db = next(get_db_for_plan(plan_id))
    return crud.get_plan_by_id(db, plan_id)


@router.post("", response_model=schemas.TravelPlanBase, status_code=status.HTTP_201_CREATED)
def create_travel_plan(plan_data: schemas.CreateTravelPlanRequest):
    """Створює новий план: UUID генеруємо тут, по ньому обираємо шард, і з ним же вставляємо"""
    new_id = uuid4()
    db = next(get_db_for_plan(new_id))
    return crud.create_plan(db, new_id, plan_data)


@router.put("/{plan_id}", response_model=schemas.TravelPlanBase)
def update_travel_plan(plan_id: UUID, plan_data: schemas.UpdateTravelPlanRequest):
    """Оновлює план у його шарді"""
    db = next(get_db_for_plan(plan_id))
    return crud.update_plan(db, plan_id, plan_data)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_plan(plan_id: UUID):
    """Видаляє план з його шарду"""
    db = next(get_db_for_plan(plan_id))
    crud.delete_plan(db, plan_id)


@router.post("/{plan_id}/locations", response_model=schemas.LocationBase, status_code=status.HTTP_201_CREATED)
def add_location_to_plan(plan_id: UUID, location_data: schemas.CreateLocationRequest):
    """Додає локацію до плану в тому ж шарді"""
    db = next(get_db_for_plan(plan_id))
    return crud.add_location(db, plan_id, location_data)