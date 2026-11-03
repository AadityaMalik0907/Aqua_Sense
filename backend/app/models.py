"""API request and response models."""

from datetime import datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TankReading(BaseModel):
    timestamp: datetime
    level: float = Field(ge=0, le=100)


class TankSummary(BaseModel):
    current_level: float = Field(ge=0, le=100)
    minimum_level: float = Field(ge=0, le=100)
    maximum_level: float = Field(ge=0, le=100)
    active_alert: bool
    historical_low_events: list[TankReading]
    readings: list[TankReading]


class DeviceStatus(BaseModel):
    id: str
    online: bool
    last_seen: datetime
    is_stale: bool
    status: str
