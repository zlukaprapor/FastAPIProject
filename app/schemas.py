from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class CreateTravelPlanRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    is_public: bool = False

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v

    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v):
        if v is not None and v < 0:
            raise ValueError('Budget must be positive')
        if v is not None:
            str_val = str(v)
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 2:
                    raise ValueError('Budget can have at most 2 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Budget exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Budget exceeds maximum precision (10 digits total)')
        return v


class UpdateTravelPlanRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    is_public: bool = False
    version: int = Field(..., ge=1)

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v

    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v):
        if v is not None:
            str_val = str(v)
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 2:
                    raise ValueError('Budget can have at most 2 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Budget exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Budget exceeds maximum precision (10 digits total)')
        return v


class TravelPlanBase(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: Optional[Decimal]
    currency: str
    is_public: bool
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: float
        }


class TravelPlanSummary(TravelPlanBase):
    location_count: int


class LocationBase(BaseModel):
    id: UUID
    travel_plan_id: UUID
    name: str
    address: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    visit_order: Optional[int] = None
    arrival_date: Optional[datetime]
    departure_date: Optional[datetime]
    budget: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: float
        }


class TravelPlanDetails(TravelPlanBase):
    locations: List[LocationBase] = []


class CreateLocationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    visit_order: Optional[int] = Field(None, ge=1)
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

    @field_validator('departure_date')
    @classmethod
    def validate_dates(cls, v, info):
        if v and info.data.get('arrival_date') and v < info.data['arrival_date']:
            raise ValueError('Departure date must be after arrival date')
        return v

    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        if v is not None:
            if v < -90 or v > 90:
                raise ValueError('Latitude must be between -90 and 90')
            # Check DECIMAL(10, 6): max 10 digits total, 6 after decimal point
            str_val = str(abs(v))
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 6:
                    raise ValueError('Latitude can have at most 6 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Latitude exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Latitude exceeds maximum precision (10 digits total)')
        return v

    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        if v is not None:
            if v < -180 or v > 180:
                raise ValueError('Longitude must be between -180 and 180')
            # Check DECIMAL(11, 6): max 11 digits total, 6 after decimal point
            str_val = str(abs(v))
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 6:
                    raise ValueError('Longitude can have at most 6 decimal places')
                if len(int_part) + len(dec_part) > 11:
                    raise ValueError('Longitude exceeds maximum precision (11 digits total)')
            elif len(str_val) > 11:
                raise ValueError('Longitude exceeds maximum precision (11 digits total)')
        return v

    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v):
        if v is not None and v < 0:
            raise ValueError('Budget must be positive')
        if v is not None:
            # Check DECIMAL(10, 2): max 10 digits total, 2 after decimal point
            str_val = str(v)
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 2:
                    raise ValueError('Budget can have at most 2 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Budget exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Budget exceeds maximum precision (10 digits total)')
        return v


class UpdateLocationRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    visit_order: Optional[int] = Field(None, ge=1)
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        if v is not None:
            if v < -90 or v > 90:
                raise ValueError('Latitude must be between -90 and 90')
            str_val = str(abs(v))
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 6:
                    raise ValueError('Latitude can have at most 6 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Latitude exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Latitude exceeds maximum precision (10 digits total)')
        return v

    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        if v is not None:
            if v < -180 or v > 180:
                raise ValueError('Longitude must be between -180 and 180')
            str_val = str(abs(v))
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 6:
                    raise ValueError('Longitude can have at most 6 decimal places')
                if len(int_part) + len(dec_part) > 11:
                    raise ValueError('Longitude exceeds maximum precision (11 digits total)')
            elif len(str_val) > 11:
                raise ValueError('Longitude exceeds maximum precision (11 digits total)')
        return v

    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v):
        if v is not None and v < 0:
            raise ValueError('Budget must be positive')
        if v is not None:
            str_val = str(v)
            if '.' in str_val:
                int_part, dec_part = str_val.split('.')
                if len(dec_part) > 2:
                    raise ValueError('Budget can have at most 2 decimal places')
                if len(int_part) + len(dec_part) > 10:
                    raise ValueError('Budget exceeds maximum precision (10 digits total)')
            elif len(str_val) > 10:
                raise ValueError('Budget exceeds maximum precision (10 digits total)')
        return v


class ErrorResponse(BaseModel):
    error: str
    details: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConflictResponse(BaseModel):
    error: str
    current_version: int
    message: str