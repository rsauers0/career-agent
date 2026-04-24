from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


class CommuteDistanceUnit(StrEnum):
    """Supported units for commute distance preferences."""

    MILES = "miles"
    KILOMETERS = "kilometers"


class WorkArrangement(StrEnum):
    """Supported work arrangement preferences."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class YearMonth(BaseModel):
    """Structured year-month value for resume-style dates without day precision."""

    year: int = Field(ge=1900, le=2100, description="Four-digit year component.")
    month: int = Field(ge=1, le=12, description="Month component from 1 to 12.")

    @model_validator(mode="before")
    @classmethod
    def parse_string_input(cls, value: Any) -> Any:
        """Allow flexible string input while normalizing to structured year/month data."""

        if not isinstance(value, str):
            return value

        normalized = value.strip()
        for fmt in ("%m/%Y", "%B %Y", "%b %Y", "%Y-%m"):
            try:
                parsed = datetime.strptime(normalized, fmt)
            except ValueError:
                continue
            return {"year": parsed.year, "month": parsed.month}

        msg = "YearMonth must be provided as MM/YYYY, Month YYYY, Mon YYYY, or YYYY-MM."
        raise ValueError(msg)

    def sort_key(self) -> tuple[int, int]:
        """Return a comparable representation for chronological ordering."""

        return (self.year, self.month)


class UserPreferences(BaseModel):
    """User-specific job search and work preference settings."""

    full_name: str = Field(min_length=1, description="The user's preferred display name.")
    base_location: str = Field(
        min_length=1,
        description=(
            "The user's home/base location, stored as a free-form city, state, "
            "and postal code string."
        ),
    )
    target_job_titles: list[str] = Field(
        default_factory=list,
        description="Job titles the user wants to target in searches and tailoring flows.",
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description="Locations the user prefers for work opportunities.",
    )
    time_zone: str | None = Field(
        default=None,
        description="Optional IANA time zone identifier, such as America/Chicago.",
    )
    preferred_work_arrangements: list[WorkArrangement] = Field(
        default_factory=list,
        description="Preferred work arrangements, such as remote, hybrid, or onsite.",
    )
    desired_salary_min: int | None = Field(
        default=None,
        ge=0,
        description="Optional minimum desired annual salary in whole currency units.",
    )
    desired_salary_max: int | None = Field(
        default=None,
        ge=0,
        description="Optional maximum desired annual salary in whole currency units.",
    )
    salary_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Currency code for desired salary values.",
    )
    max_commute_distance: int | None = Field(
        default=None,
        ge=0,
        description="Maximum acceptable one-way commute distance.",
    )
    commute_distance_unit: CommuteDistanceUnit = Field(
        default=CommuteDistanceUnit.MILES,
        description="Unit used for the maximum commute distance.",
    )
    max_commute_time: int | None = Field(
        default=None,
        ge=0,
        description="Maximum acceptable one-way commute time in minutes.",
    )
    work_authorization: bool = Field(
        description="Whether the user is legally authorized to work in the target market."
    )
    requires_work_sponsorship: bool = Field(
        description="Whether the user requires employer sponsorship to work."
    )

    @model_validator(mode="after")
    def validate_salary_range(self) -> UserPreferences:
        """Ensure the salary range is logically ordered when both values are set."""

        if (
            self.desired_salary_min is not None
            and self.desired_salary_max is not None
            and self.desired_salary_min > self.desired_salary_max
        ):
            msg = "desired_salary_min cannot be greater than desired_salary_max."
            raise ValueError(msg)

        return self

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str | None) -> str | None:
        """Validate the optional time zone against IANA zone names."""

        if value is None:
            return value

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            msg = "time_zone must be a valid IANA time zone identifier."
            raise ValueError(msg) from exc

        return value


class ExperienceEntry(BaseModel):
    """Canonical normalized representation of a single work experience entry."""

    experience_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for the experience entry.",
    )
    employer_name: str = Field(min_length=1, description="Employer or client name.")
    job_title: str = Field(min_length=1, description="Role title held for the experience.")
    location: str | None = Field(default=None, description="Location associated with the role.")
    employment_type: str | None = Field(
        default=None,
        description="Employment type, such as full-time, contract, or consulting.",
    )
    start_date: YearMonth | None = Field(
        default=None,
        description="Role start month and year.",
    )
    end_date: YearMonth | None = Field(
        default=None,
        description="Role end month and year, if applicable.",
    )
    is_current_role: bool = Field(
        default=False,
        description="Whether this experience represents the user's current role.",
    )
    role_summary: str | None = Field(
        default=None,
        description="Short normalized summary of the role and its purpose.",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Normalized list of ongoing responsibilities or ownership areas.",
    )
    accomplishments: list[str] = Field(
        default_factory=list,
        description="Normalized list of outcomes, achievements, or notable contributions.",
    )
    metrics: list[str] = Field(
        default_factory=list,
        description="Supporting quantitative facts associated with the experience.",
    )
    systems_and_tools: list[str] = Field(
        default_factory=list,
        description="Technologies, platforms, and systems used in the role.",
    )
    skills_demonstrated: list[str] = Field(
        default_factory=list,
        description="Skills and capabilities demonstrated in the role.",
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Business or industry domains relevant to the experience.",
    )
    team_context: str | None = Field(
        default=None,
        description="Context about the team structure or collaborators around the role.",
    )
    scope_notes: str | None = Field(
        default=None,
        description="Additional notes about scale, ownership, or organizational scope.",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Free-form keywords that may help with search and tailoring workflows.",
    )

    @model_validator(mode="after")
    def validate_role_dates(self) -> ExperienceEntry:
        """Ensure the role dates are logically consistent."""

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date.sort_key() < self.start_date.sort_key()
        ):
            msg = "end_date cannot be earlier than start_date."
            raise ValueError(msg)

        if self.is_current_role and self.end_date is not None:
            msg = "end_date must be None when is_current_role is True."
            raise ValueError(msg)

        return self


class CareerProfile(BaseModel):
    """Canonical structured career profile used to generate tailored job documents."""

    profile_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for the canonical career profile.",
    )
    core_narrative_notes: list[str] = Field(
        default_factory=list,
        description="User-supplied positioning notes that can later be refined into summaries.",
    )
    experience_entries: list[ExperienceEntry] = Field(
        default_factory=list,
        description="Canonical normalized work history entries.",
    )
    education_entries: list[str] = Field(
        default_factory=list,
        description=(
            "Education history entries as normalized strings until a richer model "
            "is added."
        ),
    )
    certification_entries: list[str] = Field(
        default_factory=list,
        description="Certification entries as normalized strings until a richer model is added.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Cross-role skills the user wants represented across generated documents.",
    )
    tools_and_technologies: list[str] = Field(
        default_factory=list,
        description="Cross-role tools and technologies associated with the profile.",
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Business or industry domains represented across the profile.",
    )
    notable_achievements: list[str] = Field(
        default_factory=list,
        description="Profile-level achievements that are not tied to a single role entry.",
    )
    additional_notes: str | None = Field(
        default=None,
        description="Extra canonical notes that do not fit another structured section.",
    )

    @model_validator(mode="after")
    def validate_unique_experience_ids(self) -> CareerProfile:
        """Ensure the profile does not contain duplicate experience entries."""

        seen: set[str] = set()
        for entry in self.experience_entries:
            if entry.experience_id in seen:
                msg = "experience_entries cannot contain duplicate experience_id values."
                raise ValueError(msg)
            seen.add(entry.experience_id)

        return self
