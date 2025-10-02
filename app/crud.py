from sqlalchemy.orm import Session
from sqlalchemy import func, update
from app import models, schemas
from uuid import UUID
from fastapi import HTTPException


def get_all_plans(db: Session):
    plans = db.query(
        models.TravelPlan,
        func.count(models.Location.id).label('location_count')
    ).outerjoin(models.Location).group_by(models.TravelPlan.id).all()

    result = []
    for plan, count in plans:
        plan_dict = {
            "id": plan.id,
            "title": plan.title,
            "description": plan.description,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "budget": plan.budget,
            "currency": plan.currency,
            "is_public": plan.is_public,
            "version": plan.version,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "location_count": count
        }
        result.append(plan_dict)
    return result


def get_plan_by_id(db: Session, plan_id: UUID):
    plan = db.query(models.TravelPlan).filter(models.TravelPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")
    return plan


def create_plan(db: Session, plan_data: schemas.CreateTravelPlanRequest):
    new_plan = models.TravelPlan(
        title=plan_data.title,
        description=plan_data.description,
        start_date=plan_data.start_date,
        end_date=plan_data.end_date,
        budget=plan_data.budget,
        currency=plan_data.currency,
        is_public=plan_data.is_public,
        version=1
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


def update_plan(db: Session, plan_id: UUID, plan_data: schemas.UpdateTravelPlanRequest):
    old_version = plan_data.version

    # Optimistic locking
    result = db.execute(
        update(models.TravelPlan)
        .where(models.TravelPlan.id == plan_id, models.TravelPlan.version == old_version)
        .values(
            title=plan_data.title,
            description=plan_data.description,
            start_date=plan_data.start_date,
            end_date=plan_data.end_date,
            budget=plan_data.budget,
            currency=plan_data.currency,
            is_public=plan_data.is_public,
            version=old_version + 1
        )
    )
    db.commit()

    if result.rowcount == 0:
        # Check if plan exists
        existing_plan = db.query(models.TravelPlan).filter(models.TravelPlan.id == plan_id).first()
        if not existing_plan:
            raise HTTPException(status_code=404, detail="Travel plan not found")
        # Version conflict
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": existing_plan.version,
                "message": "Please refresh and try again"
            }
        )

    # Fetch updated plan
    updated_plan = db.query(models.TravelPlan).filter(models.TravelPlan.id == plan_id).first()
    return updated_plan


def delete_plan(db: Session, plan_id: UUID):
    plan = db.query(models.TravelPlan).filter(models.TravelPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    db.delete(plan)
    db.commit()


def add_location(db: Session, plan_id: UUID, location_data: schemas.CreateLocationRequest):
    # Check if plan exists
    plan = db.query(models.TravelPlan).filter(models.TravelPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    # Use visit_order from request or let trigger auto-assign
    new_location = models.Location(
        travel_plan_id=plan_id,
        name=location_data.name,
        address=location_data.address,
        latitude=location_data.latitude,
        longitude=location_data.longitude,
        visit_order=location_data.visit_order,  # Can be None, trigger will handle it
        arrival_date=location_data.arrival_date,
        departure_date=location_data.departure_date,
        budget=location_data.budget,
        notes=location_data.notes
    )
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location


def update_location(db: Session, location_id: UUID, location_data: schemas.UpdateLocationRequest):
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = location_data.model_dump(exclude_unset=True)

    # Handle visit_order updates with constraint check
    if 'visit_order' in update_data and update_data['visit_order'] is not None:
        # Check if new visit_order conflicts with existing
        existing = db.query(models.Location).filter(
            models.Location.travel_plan_id == location.travel_plan_id,
            models.Location.visit_order == update_data['visit_order'],
            models.Location.id != location_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Visit order {update_data['visit_order']} is already taken for this travel plan"
            )

    for key, value in update_data.items():
        setattr(location, key, value)

    db.commit()
    db.refresh(location)
    return location


def delete_location(db: Session, location_id: UUID):
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    db.delete(location)
    db.commit()