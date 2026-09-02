from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Intent(str, Enum):
    QUERY = "query"
    REJECT = "reject"


class DateKind(str, Enum):
    NONE = "none"
    EXACT = "exact"
    RANGE = "range"
    RELATIVE = "relative"
    RELATIVE_MONTH_RANGE = "relative_month_range"


class RelativePeriod(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    TOMORROW = "tomorrow"
    LAST_N_DAYS = "last_n_days"
    NEXT_N_DAYS = "next_n_days"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"


Weekday = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class DateWindow(StrictModel):
    kind: DateKind = DateKind.NONE
    exact_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    relative_period: RelativePeriod | None = None
    relative_count: int | None = Field(default=None, ge=1, le=366)
    month_offset: int | None = Field(default=None, ge=-24, le=24)
    start_day: int | None = Field(default=None, ge=1, le=31)
    end_day: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def validate_shape(self) -> "DateWindow":
        if self.kind == DateKind.EXACT and self.exact_date is None:
            raise ValueError("exact_date is required for an exact date window")
        if self.kind == DateKind.RANGE:
            if self.start_date is None or self.end_date is None:
                raise ValueError("start_date and end_date are required for a range")
            if self.end_date < self.start_date:
                raise ValueError("end_date must not be before start_date")
        if self.kind == DateKind.RELATIVE and self.relative_period is None:
            raise ValueError("relative_period is required for a relative date window")
        if self.relative_period in {
            RelativePeriod.LAST_N_DAYS,
            RelativePeriod.NEXT_N_DAYS,
        } and self.relative_count is None:
            raise ValueError("relative_count is required for an N-day window")
        if self.kind == DateKind.RELATIVE_MONTH_RANGE:
            if self.month_offset is None or self.start_day is None or self.end_day is None:
                raise ValueError(
                    "month_offset, start_day, and end_day are required for a relative month range"
                )
            if self.end_day < self.start_day:
                raise ValueError("end_day must not be before start_day")
        return self


class QueryPlan(StrictModel):
    intent: Intent = Intent.QUERY
    rejection_reason: str | None = None
    camera_terms: list[str] = Field(default_factory=list, max_length=20)
    inherit_cameras: bool = False
    date_window: DateWindow = Field(default_factory=DateWindow)
    inherit_date: bool = False
    weekdays: list[Weekday] = Field(default_factory=list)
    start_time: time | None = None
    end_time: time | None = None
    inherit_time: bool = False
    reset_context: bool = False
    result_limit: int | None = Field(default=None, ge=1, le=100)
    sort_order: Literal["chronological", "latest"] = "chronological"

    @model_validator(mode="after")
    def validate_intent(self) -> "QueryPlan":
        if self.intent == Intent.REJECT and not self.rejection_reason:
            raise ValueError("rejection_reason is required for rejected requests")
        return self


class SessionContext(StrictModel):
    camera_names: list[str] = Field(default_factory=list)
    date_window: DateWindow = Field(default_factory=DateWindow)
    weekdays: list[Weekday] = Field(default_factory=list)
    start_time: time | None = None
    end_time: time | None = None


class ResolvedFilters(StrictModel):
    camera_names: list[str] = Field(default_factory=list)
    intervals_utc: list[tuple[datetime, datetime]] = Field(default_factory=list)
    date_description: str = "Any date"


class ProcessingStep(StrictModel):
    name: str
    status: Literal["passed", "completed", "rejected", "error"]
    details: dict[str, Any] = Field(default_factory=dict)


class AgentResult(StrictModel):
    status: Literal["ok", "clarification", "rejected", "error"]
    message: str
    interpreted_filters: dict[str, Any] = Field(default_factory=dict)
    records: list[dict[str, Any]] = Field(default_factory=list)
    result_count: int = Field(default=0, ge=0, le=100)
    context: SessionContext = Field(default_factory=SessionContext)
    suggestions: list[str] = Field(default_factory=list)
    processing_steps: list[ProcessingStep] = Field(default_factory=list)
