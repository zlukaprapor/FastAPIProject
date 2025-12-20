# app/crud.py
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


# ---------- helpers: types <-> Mongo ----------
def _uuid_str(u: UUID) -> str:
    return str(u)


def _to_uuid(s: str) -> UUID:
    return UUID(s)


def _now_dt() -> datetime:
    return datetime.utcnow()


def _date_to_str(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _str_to_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v)
    if isinstance(v, datetime):
        return v.date()
    raise ValueError("Unsupported date value")


def _dec(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    # надійно: float/int/str -> Decimal
    return Decimal(str(v))


def _float(v: Optional[Decimal]) -> Optional[float]:
    if v is None:
        return None
    return float(v)


# ---------- indexes ----------
async def ensure_indexes(db) -> None:
    # для підрахунків/фільтрів
    await db.travel_plans.create_index("updated_at")
    # унікальний visit_order в межах plan
    await db.locations.create_index([("travel_plan_id", 1), ("visit_order", 1)], unique=True)
    await db.locations.create_index("travel_plan_id")


# ---------- travel plans ----------
async def get_all_plans(db) -> List[Dict[str, Any]]:
    plans = await db.travel_plans.find({}).to_list(length=10000)

    # counts
    pipeline = [{"$group": {"_id": "$travel_plan_id", "cnt": {"$sum": 1}}}]
    counts = await db.locations.aggregate(pipeline).to_list(length=100000)
    count_map = {c["_id"]: int(c["cnt"]) for c in counts}

    out: List[Dict[str, Any]] = []
    for p in plans:
        pid = p["_id"]  # string uuid
        out.append({
            "id": _to_uuid(pid),
            "title": p.get("title"),
            "description": p.get("description"),
            "start_date": _str_to_date(p.get("start_date")),
            "end_date": _str_to_date(p.get("end_date")),
            "budget": _dec(p.get("budget")),
            "currency": p.get("currency"),
            "is_public": p.get("is_public", False),
            "version": int(p.get("version", 1)),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "location_count": count_map.get(pid, 0),
        })
    return out


async def get_plan_by_id(db, plan_id: UUID) -> Dict[str, Any]:
    pid = _uuid_str(plan_id)

    plan = await db.travel_plans.find_one({"_id": pid})
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    locations = await db.locations.find({"travel_plan_id": pid}).sort("visit_order", 1).to_list(length=100000)

    return {
        "id": _to_uuid(plan["_id"]),
        "title": plan.get("title"),
        "description": plan.get("description"),
        "start_date": _str_to_date(plan.get("start_date")),
        "end_date": _str_to_date(plan.get("end_date")),
        "budget": _dec(plan.get("budget")),
        "currency": plan.get("currency"),
        "is_public": plan.get("is_public", False),
        "version": int(plan.get("version", 1)),
        "created_at": plan.get("created_at"),
        "updated_at": plan.get("updated_at"),
        "locations": [
            {
                "id": _to_uuid(loc["_id"]),
                "travel_plan_id": _to_uuid(loc["travel_plan_id"]),
                "name": loc.get("name"),
                "address": loc.get("address"),
                "latitude": _dec(loc.get("latitude")),
                "longitude": _dec(loc.get("longitude")),
                "visit_order": loc.get("visit_order"),
                "arrival_date": loc.get("arrival_date"),
                "departure_date": loc.get("departure_date"),
                "budget": _dec(loc.get("budget")),
                "notes": loc.get("notes"),
                "created_at": loc.get("created_at"),
            }
            for loc in locations
        ],
    }


async def create_plan(db, plan_data) -> Dict[str, Any]:
    new_id = str(uuid4())

    doc = {
        "_id": new_id,
        "title": plan_data.title,
        "description": plan_data.description,
        "start_date": _date_to_str(plan_data.start_date),  # date -> "YYYY-MM-DD"
        "end_date": _date_to_str(plan_data.end_date),
        "budget": _float(plan_data.budget),  # Decimal -> float
        "currency": plan_data.currency,
        "is_public": plan_data.is_public,
        "version": 1,
        "created_at": _now_dt(),
        "updated_at": _now_dt(),
    }

    await db.travel_plans.insert_one(doc)

    return {
        "id": _to_uuid(doc["_id"]),
        "title": doc["title"],
        "description": doc["description"],
        "start_date": _str_to_date(doc["start_date"]),
        "end_date": _str_to_date(doc["end_date"]),
        "budget": _dec(doc["budget"]),
        "currency": doc["currency"],
        "is_public": doc["is_public"],
        "version": doc["version"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


async def update_plan(db, plan_id: UUID, plan_data) -> Dict[str, Any]:
    pid = _uuid_str(plan_id)
    old_version = int(plan_data.version)

    update_doc = {
        "title": plan_data.title,
        "description": plan_data.description,
        "start_date": _date_to_str(plan_data.start_date),
        "end_date": _date_to_str(plan_data.end_date),
        "budget": _float(plan_data.budget),
        "currency": plan_data.currency,
        "is_public": plan_data.is_public,
        "updated_at": _now_dt(),
    }

    updated = await db.travel_plans.find_one_and_update(
        {"_id": pid, "version": old_version},
        {"$set": update_doc, "$inc": {"version": 1}},
        return_document=ReturnDocument.AFTER
    )

    if not updated:
        existing = await db.travel_plans.find_one({"_id": pid})
        if not existing:
            raise HTTPException(status_code=404, detail="Travel plan not found")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int(existing.get("version", 1)),
                "message": "Please refresh and try again",
            }
        )

    return {
        "id": _to_uuid(updated["_id"]),
        "title": updated.get("title"),
        "description": updated.get("description"),
        "start_date": _str_to_date(updated.get("start_date")),
        "end_date": _str_to_date(updated.get("end_date")),
        "budget": _dec(updated.get("budget")),
        "currency": updated.get("currency"),
        "is_public": updated.get("is_public", False),
        "version": int(updated.get("version", 1)),
        "created_at": updated.get("created_at"),
        "updated_at": updated.get("updated_at"),
    }


async def delete_plan(db, plan_id: UUID) -> None:
    pid = _uuid_str(plan_id)

    res = await db.travel_plans.delete_one({"_id": pid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    await db.locations.delete_many({"travel_plan_id": pid})


# ---------- locations ----------
async def add_location(db, plan_id: UUID, location_data) -> Dict[str, Any]:
    pid = _uuid_str(plan_id)

    plan = await db.travel_plans.find_one({"_id": pid})
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    if int(plan.get("version", 1)) != int(location_data.plan_version):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int(plan.get("version", 1)),
                "message": "Please refresh the plan and try again",
            }
        )

    # visit_order auto
    visit_order = location_data.visit_order
    if visit_order is None:
        last = await db.locations.find({"travel_plan_id": pid}).sort("visit_order", -1).limit(1).to_list(length=1)
        visit_order = 1 if not last else int(last[0].get("visit_order", 0)) + 1
    visit_order = int(visit_order)

    # bump plan version atomically
    bumped = await db.travel_plans.find_one_and_update(
        {"_id": pid, "version": int(location_data.plan_version)},
        {"$inc": {"version": 1}, "$set": {"updated_at": _now_dt()}},
        return_document=ReturnDocument.AFTER
    )
    if not bumped:
        current = await db.travel_plans.find_one({"_id": pid})
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int((current or {}).get("version", 1)),
                "message": "Please refresh the plan and try again",
            }
        )

    loc_id = str(uuid4())
    loc_doc = {
        "_id": loc_id,
        "travel_plan_id": pid,
        "name": location_data.name,
        "address": location_data.address,
        "latitude": _float(location_data.latitude),
        "longitude": _float(location_data.longitude),
        "visit_order": visit_order,
        "arrival_date": location_data.arrival_date,      # datetime stays datetime
        "departure_date": location_data.departure_date,  # datetime stays datetime
        "budget": _float(location_data.budget),
        "notes": location_data.notes,
        "created_at": _now_dt(),
    }

    try:
        await db.locations.insert_one(loc_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail=f"Visit order {visit_order} is already taken for this travel plan"
        )

    return {
        "id": _to_uuid(loc_doc["_id"]),
        "travel_plan_id": _to_uuid(loc_doc["travel_plan_id"]),
        "name": loc_doc["name"],
        "address": loc_doc["address"],
        "latitude": _dec(loc_doc["latitude"]),
        "longitude": _dec(loc_doc["longitude"]),
        "visit_order": loc_doc["visit_order"],
        "arrival_date": loc_doc["arrival_date"],
        "departure_date": loc_doc["departure_date"],
        "budget": _dec(loc_doc["budget"]),
        "notes": loc_doc["notes"],
        "created_at": loc_doc["created_at"],
    }


async def update_location(db, location_id: UUID, location_data) -> Dict[str, Any]:
    lid = _uuid_str(location_id)

    loc = await db.locations.find_one({"_id": lid})
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    pid = loc["travel_plan_id"]

    plan = await db.travel_plans.find_one({"_id": pid})
    if not plan:
        raise HTTPException(status_code=404, detail="Travel plan not found")

    old_version = int(location_data.plan_version)
    if int(plan.get("version", 1)) != old_version:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int(plan.get("version", 1)),
                "message": "Please refresh the plan and try again",
            }
        )

    update_data = location_data.model_dump(exclude_unset=True, exclude={"plan_version"})

    # Decimal -> float for storing
    if "latitude" in update_data:
        update_data["latitude"] = _float(update_data["latitude"])
    if "longitude" in update_data:
        update_data["longitude"] = _float(update_data["longitude"])
    if "budget" in update_data:
        update_data["budget"] = _float(update_data["budget"])

    if "visit_order" in update_data and update_data["visit_order"] is not None:
        vo = int(update_data["visit_order"])
        existing = await db.locations.find_one({
            "travel_plan_id": pid,
            "visit_order": vo,
            "_id": {"$ne": lid}
        })
        if existing:
            raise HTTPException(status_code=409, detail=f"Visit order {vo} is already taken for this travel plan")
        update_data["visit_order"] = vo

    # bump plan version atomically
    bumped = await db.travel_plans.find_one_and_update(
        {"_id": pid, "version": old_version},
        {"$inc": {"version": 1}, "$set": {"updated_at": _now_dt()}},
        return_document=ReturnDocument.AFTER
    )
    if not bumped:
        current = await db.travel_plans.find_one({"_id": pid})
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int((current or {}).get("version", 1)),
                "message": "Please refresh the plan and try again",
            }
        )

    await db.locations.update_one({"_id": lid}, {"$set": update_data})
    updated = await db.locations.find_one({"_id": lid})

    return {
        "id": _to_uuid(updated["_id"]),
        "travel_plan_id": _to_uuid(updated["travel_plan_id"]),
        "name": updated.get("name"),
        "address": updated.get("address"),
        "latitude": _dec(updated.get("latitude")),
        "longitude": _dec(updated.get("longitude")),
        "visit_order": updated.get("visit_order"),
        "arrival_date": updated.get("arrival_date"),
        "departure_date": updated.get("departure_date"),
        "budget": _dec(updated.get("budget")),
        "notes": updated.get("notes"),
        "created_at": updated.get("created_at"),
    }


async def delete_location(db, location_id: UUID, plan_version: int) -> None:
    lid = _uuid_str(location_id)

    loc = await db.locations.find_one({"_id": lid})
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    pid = loc["travel_plan_id"]

    bumped = await db.travel_plans.find_one_and_update(
        {"_id": pid, "version": int(plan_version)},
        {"$inc": {"version": 1}, "$set": {"updated_at": _now_dt()}},
        return_document=ReturnDocument.AFTER
    )
    if not bumped:
        current = await db.travel_plans.find_one({"_id": pid})
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict: Travel plan was modified by another user",
                "current_version": int((current or {}).get("version", 1)),
                "message": "Please refresh the plan and try again",
            }
        )

    await db.locations.delete_one({"_id": lid})
