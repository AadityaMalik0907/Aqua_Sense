"""API request and response models."""

from datetime import datetime
from typing import Any, Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator
from .time_utils import parse_and_normalize_timestamp, validate_not_future


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TankReading(BaseModel):
    timestamp: datetime
    level: float = Field(ge=0, le=100, validation_alias=AliasChoices("level", "level_percent"))

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_and_normalize_timestamp(cls, value: Any) -> datetime:
        """Enforce timezone awareness, normalize to UTC, and reject future timestamps."""
        utc_dt = parse_and_normalize_timestamp(value)
        validate_not_future(utc_dt)
        return utc_dt


class TankSummary(BaseModel):
    current_level: float = Field(ge=0, le=100)
    minimum_level: float = Field(ge=0, le=100)
    maximum_level: float = Field(ge=0, le=100)
    active_alert: bool
    historical_low_events: list[TankReading]
    readings: list[TankReading]
    # Backward-compatible freshness metadata
    is_stale: bool = False
    latest_reading_timestamp: datetime | None = None


class DeviceStatus(BaseModel):
    id: str
    online: bool
    last_seen: datetime
    is_stale: bool
    status: str
    level_percent: float = Field(ge=0, le=100, default=55.0, validation_alias=AliasChoices("level_percent", "level"))
    pump_state: Literal["on", "off"] = "off"
