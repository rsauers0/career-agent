from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class CommuteDistanceUnit(StrEnum):
    """Supported units for commute distance preferences."""

    MILES = "miles"
    KILOMETERS = "kilometers"


class WorkArrangement(StrEnum):
    """Supported work arrangement preferences."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EmploymentType(StrEnum):
    """Common employment type values for experience entries."""

    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    CONSULTING = "consulting"
    INTERNSHIP = "internship"
    OTHER = "other"


class ExperienceIntakeStatus(StrEnum):
    """Workflow states for one role-specific experience intake session."""

    DRAFT = "draft"
    SOURCE_CAPTURED = "source_captured"
    QUESTIONS_GENERATED = "questions_generated"
    ANSWERS_CAPTURED = "answers_captured"
    DRAFT_GENERATED = "draft_generated"
    ACCEPTED = "accepted"
    ABANDONED = "abandoned"


class IntakeMessageRole(StrEnum):
    """Supported transcript message roles for intake workflows."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def validate_iana_time_zone(value: str | None) -> str | None:
    """Validate an optional IANA time zone identifier."""

    if value is None:
        return value

    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        msg = "time_zone must be a valid IANA time zone identifier."
        raise ValueError(msg) from exc

    return value


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

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str | None) -> str | None:
        """Validate the optional time zone against IANA zone names."""

        return validate_iana_time_zone(value)


class ExperienceEntry(BaseModel):
    """Canonical normalized representation of a single work experience entry."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        validation_alias=AliasChoices("id", "experience_id"),
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


class IntakeMessage(BaseModel):
    """One retained transcript message from an experience intake workflow."""

    role: IntakeMessageRole = Field(description="Message author role.")
    content: str = Field(min_length=1, description="Message content.")
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at_timezone(cls, value: datetime) -> datetime:
        """Ensure retained transcript timestamps are timezone-aware."""

        return validate_timezone_aware(value, "created_at")


class IntakeQuestion(BaseModel):
    """One structured follow-up question generated during intake."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for the intake question.",
    )
    question: str = Field(min_length=1, description="Question to ask the user.")
    rationale: str | None = Field(
        default=None,
        description="Optional explanation of why the question matters.",
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at_timezone(cls, value: datetime) -> datetime:
        """Ensure question timestamps are timezone-aware."""

        return validate_timezone_aware(value, "created_at")


class IntakeAnswer(BaseModel):
    """One user answer to a structured intake question."""

    question_id: str = Field(min_length=1, description="Identifier of the answered question.")
    answer: str = Field(min_length=1, description="User-provided answer.")
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timezone-aware UTC creation timestamp.",
    )

    @field_validator("created_at")
    @classmethod
    def validate_created_at_timezone(cls, value: datetime) -> datetime:
        """Ensure answer timestamps are timezone-aware."""

        return validate_timezone_aware(value, "created_at")


class ExperienceIntakeSession(BaseModel):
    """Recoverable workflow state for creating one future experience entry."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable identifier for the intake session.",
    )
    status: ExperienceIntakeStatus = Field(
        default=ExperienceIntakeStatus.DRAFT,
        description="Current intake workflow state.",
    )
    source_text: str | None = Field(
        default=None,
        description="Raw source bullets or notes for one role-specific experience.",
    )
    employer_name: str | None = Field(
        default=None,
        description="Employer or client name for the future experience entry.",
    )
    job_title: str | None = Field(
        default=None,
        description="Role title for the future experience entry.",
    )
    location: str | None = Field(
        default=None,
        description="Optional role location for the future experience entry.",
    )
    employment_type: str | None = Field(
        default=None,
        description="Optional employment type for the future experience entry.",
    )
    start_date: YearMonth | None = Field(
        default=None,
        description="Role start month and year for the future experience entry.",
    )
    end_date: YearMonth | None = Field(
        default=None,
        description="Role end month and year for the future experience entry.",
    )
    is_current_role: bool = Field(
        default=False,
        description="Whether this intake represents the user's current role.",
    )
    transcript: list[IntakeMessage] = Field(
        default_factory=list,
        description="Retained local transcript for development traceability.",
    )
    follow_up_questions: list[IntakeQuestion] = Field(
        default_factory=list,
        description="Structured follow-up questions generated for this intake.",
    )
    user_answers: list[IntakeAnswer] = Field(
        default_factory=list,
        description="User answers to generated follow-up questions.",
    )
    draft_experience_entry: ExperienceEntry | None = Field(
        default=None,
        description="Draft structured experience entry awaiting review or acceptance.",
    )
    accepted_experience_entry_id: str | None = Field(
        default=None,
        description="Identifier of the accepted canonical experience entry, if any.",
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timezone-aware UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Timezone-aware UTC update timestamp.",
    )

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timestamp_timezone(cls, value: datetime) -> datetime:
        """Ensure intake session timestamps are timezone-aware."""

        return validate_timezone_aware(value, "timestamp")

    @model_validator(mode="after")
    def validate_acceptance_link(self) -> ExperienceIntakeSession:
        """Ensure accepted intake sessions link to their accepted experience entry."""

        if self.status is ExperienceIntakeStatus.ACCEPTED:
            if not self.accepted_experience_entry_id:
                msg = "accepted_experience_entry_id is required when status is accepted."
                raise ValueError(msg)
            if (
                self.draft_experience_entry is not None
                and self.accepted_experience_entry_id != self.draft_experience_entry.id
            ):
                msg = "accepted_experience_entry_id must match draft_experience_entry.id."
                raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_role_dates(self) -> ExperienceIntakeSession:
        """Ensure intake role dates are logically consistent."""

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
            "Education history entries as normalized strings until a richer model is added."
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
    def validate_unique_experience_entry_ids(self) -> CareerProfile:
        """Ensure the profile does not contain duplicate experience entries."""

        seen: set[str] = set()
        for entry in self.experience_entries:
            if entry.id in seen:
                msg = "experience_entries cannot contain duplicate id values."
                raise ValueError(msg)
            seen.add(entry.id)

        return self


def validate_timezone_aware(value: datetime, field_name: str) -> datetime:
    """Validate that a timestamp includes timezone information."""

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"{field_name} must be timezone-aware."
        raise ValueError(msg)
    return value
