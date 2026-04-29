from __future__ import annotations

from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class CommuteDistanceUnit(StrEnum):
    """Supported units for commute distance preferences."""

    MILES = "miles"
    KILOMETERS = "kilometers"


class WorkArrangement(StrEnum):
    """Supported work arrangement preferences."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class UserPreferences(BaseModel):
    """User-specific job search and matching preferences."""

    full_name: str = Field(
        min_length=1,
        description="User's preferred display name.",
    )
    base_location: str = Field(
        min_length=1,
        description="User's home or base location, such as city, state, and postal code.",
    )
    time_zone: str | None = Field(
        default=None,
        description="Optional IANA time zone identifier, such as America/Chicago.",
    )
    target_job_titles: list[str] = Field(
        default_factory=list,
        description="Job titles the user may want to target.",
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description="Locations the user prefers or is willing to consider.",
    )
    preferred_work_arrangements: list[WorkArrangement] = Field(
        min_length=1,
        description="Preferred work arrangements, such as remote, hybrid, or onsite.",
    )
    desired_salary_min: int | None = Field(
        default=None,
        ge=0,
        description="Optional minimum desired annual salary in whole currency units.",
    )
    salary_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO-style three-letter currency code for salary values.",
    )
    max_commute_distance: int | None = Field(
        default=None,
        ge=0,
        description="Optional maximum acceptable one-way commute distance.",
    )
    commute_distance_unit: CommuteDistanceUnit = Field(
        default=CommuteDistanceUnit.MILES,
        description="Unit used for max_commute_distance.",
    )
    max_commute_time: int | None = Field(
        default=None,
        ge=0,
        description="Optional maximum acceptable one-way commute time in minutes.",
    )
    work_authorization: bool = Field(
        description="Whether the user is legally authorized to work in the target market.",
    )
    requires_work_sponsorship: bool = Field(
        description="Whether the user requires employer sponsorship to work.",
    )

    @field_validator("full_name", "base_location", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("time_zone", mode="before")
    @classmethod
    def normalize_optional_time_zone(cls, value: str | None) -> str | None:
        """Trim optional time zone input and treat blanks as unset."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str | None) -> str | None:
        """Validate optional time zone values against IANA identifiers."""

        if value is None:
            return None

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            msg = "time_zone must be a valid IANA time zone identifier."
            raise ValueError(msg) from exc

        return value

    @field_validator("target_job_titles", "preferred_locations", mode="before")
    @classmethod
    def normalize_text_list(cls, values: list[str] | None) -> list[str]:
        """Trim list items and discard blank entries."""

        if values is None:
            return []
        return [value.strip() for value in values if value.strip()]

    @field_validator("salary_currency", mode="before")
    @classmethod
    def normalize_salary_currency(cls, value: str) -> str:
        """Normalize currency code casing before validation."""

        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("salary_currency")
    @classmethod
    def validate_salary_currency(cls, value: str) -> str:
        """Validate that salary currency is a three-letter alphabetic code."""

        if not value.isalpha():
            msg = "salary_currency must be a three-letter alphabetic currency code."
            raise ValueError(msg)
        return value
