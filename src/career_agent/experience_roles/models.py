from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class EmploymentType(StrEnum):
    """Supported employment type values for experience roles."""

    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    CONSULTING = "consulting"
    INTERNSHIP = "internship"
    OTHER = "other"


class ExperienceRoleStatus(StrEnum):
    """User-facing review status for an experience role."""

    INPUT_REQUIRED = "input_required"
    REVIEW_REQUIRED = "review_required"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class YearMonth(BaseModel):
    """Month/year value for resume-style dates without day precision."""

    year: int = Field(ge=1900, le=2100, description="Four-digit year.")
    month: int = Field(ge=1, le=12, description="Month number from 1 to 12.")

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, value: Any) -> Any:
        """Allow common string formats while storing structured year/month data."""

        if not isinstance(value, str):
            return value

        normalized = value.strip()
        for date_format in ("%m/%Y", "%B %Y", "%b %Y", "%Y-%m"):
            try:
                parsed = datetime.strptime(normalized, date_format)
            except ValueError:
                continue
            return {"year": parsed.year, "month": parsed.month}

        msg = "YearMonth must be provided as MM/YYYY, Month YYYY, Mon YYYY, or YYYY-MM."
        raise ValueError(msg)

    def sort_key(self) -> tuple[int, int]:
        """Return a comparable chronological key."""

        return (self.year, self.month)


class ExperienceRole(BaseModel):
    """Role-level container for one job or position in the career profile."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for this experience role.",
    )
    employer_name: str = Field(
        min_length=1,
        description="Employer, client, or organization name.",
    )
    job_title: str = Field(
        min_length=1,
        description="Role title held by the user.",
    )
    location: str | None = Field(
        default=None,
        description="Optional role location.",
    )
    employment_type: EmploymentType | None = Field(
        default=None,
        description="Optional employment type.",
    )
    role_focus: str | None = Field(
        default=None,
        description=(
            "User-authored 1-2 sentence explanation of the role's primary focus. "
            "Used as workflow context, not as a polished resume summary."
        ),
    )
    start_date: YearMonth = Field(
        description="Role start month and year.",
    )
    end_date: YearMonth | None = Field(
        default=None,
        description="Role end month and year, unless this is a current role.",
    )
    is_current_role: bool = Field(
        default=False,
        description="Whether this role is currently held by the user.",
    )
    status: ExperienceRoleStatus = Field(
        default=ExperienceRoleStatus.INPUT_REQUIRED,
        description="User-facing workflow status for this role.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("employer_name", "job_title", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Any) -> Any:
        """Trim required text fields before normal Pydantic validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("location", "role_focus", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        """Trim optional text fields and treat blanks as unset."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        """Ensure timestamps are timezone-aware."""

        if value.tzinfo is None:
            msg = "timestamp values must be timezone-aware."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_role_dates(self) -> ExperienceRole:
        """Ensure role dates are logically consistent."""

        if self.is_current_role and self.end_date is not None:
            msg = "end_date must be empty when is_current_role is true."
            raise ValueError(msg)

        if not self.is_current_role and self.end_date is None:
            msg = "end_date is required when is_current_role is false."
            raise ValueError(msg)

        if self.end_date is not None and self.end_date.sort_key() < self.start_date.sort_key():
            msg = "end_date cannot be earlier than start_date."
            raise ValueError(msg)

        return self
