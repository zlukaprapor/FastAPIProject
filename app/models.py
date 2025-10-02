from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, Date, Text, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    budget = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    is_public = Column(Boolean, nullable=False, default=False, server_default="false")
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    locations = relationship("Location", back_populates="travel_plan", cascade="all, delete-orphan", order_by="Location.visit_order")

    __table_args__ = (
        CheckConstraint("LENGTH(TRIM(title)) > 0", name="check_title_not_empty"),
        CheckConstraint("LENGTH(currency) = 3", name="check_currency_length"),
        CheckConstraint("version > 0", name="check_version_positive"),
        CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="check_dates"),
        CheckConstraint("budget IS NULL OR budget >= 0", name="check_budget"),
        Index("idx_travel_plans_dates", "start_date", "end_date", postgresql_where=Column("start_date").isnot(None)),
        Index("idx_travel_plans_public", "is_public", "updated_at", postgresql_where=Column("is_public") == True),
        Index("idx_travel_plans_updated", "updated_at", postgresql_using="btree", postgresql_ops={"updated_at": "DESC"}),
    )


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    travel_plan_id = Column(UUID(as_uuid=True), ForeignKey("travel_plans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Numeric(10, 6), nullable=True)
    longitude = Column(Numeric(11, 6), nullable=True)
    visit_order = Column(Integer, nullable=True)  # Nullable because trigger auto-assigns
    arrival_date = Column(DateTime(timezone=True), nullable=True)
    departure_date = Column(DateTime(timezone=True), nullable=True)
    budget = Column(Numeric(10, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    travel_plan = relationship("TravelPlan", back_populates="locations")

    __table_args__ = (
        CheckConstraint("LENGTH(TRIM(name)) > 0", name="check_name_not_empty"),
        CheckConstraint("visit_order IS NULL OR visit_order > 0", name="check_visit_order_positive"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="check_coordinates_lat"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="check_coordinates_lng"),
        CheckConstraint("departure_date IS NULL OR arrival_date IS NULL OR departure_date >= arrival_date", name="check_location_dates"),
        CheckConstraint("budget IS NULL OR budget >= 0", name="check_location_budget"),
        UniqueConstraint("travel_plan_id", "visit_order", name="unique_plan_order"),
        Index("idx_locations_plan_order", "travel_plan_id", "visit_order"),
        Index("idx_locations_coordinates", "latitude", "longitude", postgresql_where=Column("latitude").isnot(None) & Column("longitude").isnot(None)),
    )