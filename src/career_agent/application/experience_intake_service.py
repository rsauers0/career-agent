from __future__ import annotations

from career_agent.application.ports import (
    ExperienceIntakeAssistant,
    ExperienceIntakeRepository,
    ProfileRepository,
)
from career_agent.domain.models import (
    CareerProfile,
    ExperienceEntry,
    ExperienceIntakeSession,
    ExperienceIntakeStatus,
    IntakeAnswer,
    YearMonth,
    utc_now,
)


class ExperienceIntakeService:
    """Application service for recoverable experience intake workflows."""

    def __init__(
        self,
        repository: ExperienceIntakeRepository,
        assistant: ExperienceIntakeAssistant | None = None,
        profile_repository: ProfileRepository | None = None,
    ) -> None:
        self.repository = repository
        self.assistant = assistant
        self.profile_repository = profile_repository

    def create_session(self) -> ExperienceIntakeSession:
        """Create and persist a new draft intake session."""

        session = ExperienceIntakeSession()
        self.repository.save_session(session)
        return session

    def get_session(self, session_id: str) -> ExperienceIntakeSession | None:
        """Return a stored intake session if it exists."""

        return self.repository.load_session(session_id)

    def list_sessions(self) -> list[ExperienceIntakeSession]:
        """Return all stored intake sessions."""

        return self.repository.list_sessions()

    def list_sessions_by_status(
        self,
        status: ExperienceIntakeStatus,
    ) -> list[ExperienceIntakeSession]:
        """Return stored intake sessions matching a status."""

        return self.repository.list_sessions_by_status(status)

    def delete_session(self, session_id: str) -> None:
        """Delete an unlocked intake session."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status in {ExperienceIntakeStatus.LOCKED, ExperienceIntakeStatus.ACCEPTED}:
            msg = "Locked experience intake entries cannot be deleted."
            raise ValueError(msg)

        self.repository.delete_session(session_id)

    def capture_source_text(
        self,
        session_id: str,
        source_text: str,
        *,
        append: bool = False,
    ) -> ExperienceIntakeSession:
        """Store role-specific source text for an existing intake session."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        normalized_source_text = source_text.strip()
        if not normalized_source_text:
            msg = "Experience intake source text is required."
            raise ValueError(msg)

        if append and session.source_text:
            normalized_source_text = f"{session.source_text.rstrip()}\n\n{normalized_source_text}"

        updated = session.model_copy(
            update={
                "source_text": normalized_source_text,
                "status": ExperienceIntakeStatus.SOURCE_CAPTURED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def capture_role_details(
        self,
        session_id: str,
        *,
        employer_name: str,
        job_title: str,
        location: str | None = None,
        employment_type: str | None = None,
        start_date: YearMonth | str | dict[str, int] | None = None,
        end_date: YearMonth | str | dict[str, int] | None = None,
        is_current_role: bool = False,
    ) -> ExperienceIntakeSession:
        """Store role metadata needed for the future canonical experience entry."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        normalized_employer_name = employer_name.strip()
        normalized_job_title = job_title.strip()
        if not normalized_employer_name:
            msg = "Experience intake employer name is required."
            raise ValueError(msg)
        if not normalized_job_title:
            msg = "Experience intake job title is required."
            raise ValueError(msg)

        normalized_location = self._normalize_optional_text(location)
        normalized_employment_type = self._normalize_optional_text(employment_type)
        normalized_start_date = self._normalize_year_month(start_date, "start_date")
        normalized_end_date = self._normalize_year_month(end_date, "end_date")
        if is_current_role:
            normalized_end_date = None

        updated = session.model_copy(
            update={
                "employer_name": normalized_employer_name,
                "job_title": normalized_job_title,
                "location": normalized_location,
                "employment_type": normalized_employment_type,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
                "is_current_role": is_current_role,
                "updated_at": utc_now(),
            }
        )
        updated = ExperienceIntakeSession.model_validate(updated.model_dump())
        self.repository.save_session(updated)
        return updated

    def capture_answers(
        self,
        session_id: str,
        answers_by_question_id: dict[str, str],
    ) -> ExperienceIntakeSession:
        """Store user answers for generated follow-up questions."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status not in {
            ExperienceIntakeStatus.QUESTIONS_GENERATED,
            ExperienceIntakeStatus.ANSWERS_CAPTURED,
        }:
            msg = "Experience intake questions must be generated before capturing answers."
            raise ValueError(msg)

        if not session.follow_up_questions:
            msg = "Experience intake follow-up questions are required before capturing answers."
            raise ValueError(msg)

        question_ids = {question.id for question in session.follow_up_questions}
        answer_ids = set(answers_by_question_id)
        unknown_question_ids = sorted(answer_ids - question_ids)
        if unknown_question_ids:
            msg = f"Unknown follow-up question IDs: {', '.join(unknown_question_ids)}."
            raise ValueError(msg)

        missing_question_ids = sorted(question_ids - answer_ids)
        if missing_question_ids:
            msg = f"Missing answers for follow-up question IDs: {', '.join(missing_question_ids)}."
            raise ValueError(msg)

        answers = []
        for question in session.follow_up_questions:
            answer = answers_by_question_id[question.id].strip()
            if not answer:
                msg = f"Answer cannot be blank for follow-up question ID: {question.id}."
                raise ValueError(msg)
            answers.append(IntakeAnswer(question_id=question.id, answer=answer))

        updated = session.model_copy(
            update={
                "user_answers": answers,
                "status": ExperienceIntakeStatus.ANSWERS_CAPTURED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def generate_draft_entry(self, session_id: str) -> ExperienceIntakeSession:
        """Generate and store a draft experience entry from answered intake data."""

        if self.assistant is None:
            msg = "Experience intake assistant is not configured."
            raise RuntimeError(msg)

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status not in {
            ExperienceIntakeStatus.ANSWERS_CAPTURED,
            ExperienceIntakeStatus.DRAFT_GENERATED,
        }:
            msg = "Experience intake answers must be captured before generating a draft."
            raise ValueError(msg)

        self._validate_ready_for_draft(session)

        draft = self.assistant.draft_experience_entry(session)
        draft = self._normalize_draft_role_details(session, draft)

        updated = session.model_copy(
            update={
                "draft_experience_entry": draft,
                "status": ExperienceIntakeStatus.DRAFT_GENERATED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def update_draft_entry(
        self,
        session_id: str,
        draft: ExperienceEntry,
    ) -> ExperienceIntakeSession:
        """Update a generated draft before it is locked into the career profile."""

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status in {ExperienceIntakeStatus.LOCKED, ExperienceIntakeStatus.ACCEPTED}:
            msg = (
                "Locked experience intake entries cannot be edited through the draft "
                "update workflow."
            )
            raise ValueError(msg)

        if session.status is not ExperienceIntakeStatus.DRAFT_GENERATED:
            msg = "Experience intake draft must be generated before it can be updated."
            raise ValueError(msg)

        if session.draft_experience_entry is None:
            msg = "Experience intake draft entry is required before updating it."
            raise ValueError(msg)

        normalized_draft = draft.model_copy(
            update={
                "id": session.draft_experience_entry.id,
                "employer_name": session.employer_name or draft.employer_name,
                "job_title": session.job_title or draft.job_title,
                "location": session.location or draft.location,
                "employment_type": session.employment_type or draft.employment_type,
                "start_date": session.start_date or draft.start_date,
                "end_date": None if session.is_current_role else session.end_date or draft.end_date,
                "is_current_role": session.is_current_role,
            }
        )

        updated = session.model_copy(
            update={
                "draft_experience_entry": normalized_draft,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def lock_draft_entry(self, session_id: str) -> ExperienceIntakeSession:
        """Lock a draft experience entry into the canonical career profile."""

        if self.profile_repository is None:
            msg = "Profile repository is not configured for locking experience entries."
            raise RuntimeError(msg)

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status not in {
            ExperienceIntakeStatus.DRAFT_GENERATED,
            ExperienceIntakeStatus.LOCKED,
            ExperienceIntakeStatus.ACCEPTED,
        }:
            msg = "Experience intake draft must be generated before locking it."
            raise ValueError(msg)

        if session.draft_experience_entry is None:
            msg = "Experience intake draft entry is required before locking it."
            raise ValueError(msg)

        profile = self.profile_repository.load_career_profile() or CareerProfile()
        profile = self._upsert_experience_entry(profile, session.draft_experience_entry)
        self.profile_repository.save_career_profile(profile)
        locked_at = utc_now()

        updated = session.model_copy(
            update={
                "accepted_experience_entry_id": session.draft_experience_entry.id,
                "status": ExperienceIntakeStatus.LOCKED,
                "locked_at": locked_at,
                "updated_at": locked_at,
            }
        )
        self.repository.save_session(updated)
        return updated

    def accept_draft_entry(self, session_id: str) -> ExperienceIntakeSession:
        """Compatibility wrapper for the older accept terminology."""

        return self.lock_draft_entry(session_id)

    def generate_follow_up_questions(self, session_id: str) -> ExperienceIntakeSession:
        """Generate and store follow-up questions for captured source text."""

        if self.assistant is None:
            msg = "Experience intake assistant is not configured."
            raise RuntimeError(msg)

        session = self.repository.load_session(session_id)
        if session is None:
            msg = f"Experience intake session not found: {session_id}."
            raise ValueError(msg)

        if session.status is not ExperienceIntakeStatus.SOURCE_CAPTURED:
            msg = "Experience intake source text must be captured before generating questions."
            raise ValueError(msg)

        if not session.source_text:
            msg = "Experience intake source text is required before generating questions."
            raise ValueError(msg)

        questions = self.assistant.generate_follow_up_questions(session)
        if not questions:
            msg = "Experience intake assistant returned no follow-up questions."
            raise ValueError(msg)

        updated = session.model_copy(
            update={
                "follow_up_questions": questions,
                "status": ExperienceIntakeStatus.QUESTIONS_GENERATED,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_session(updated)
        return updated

    def _validate_ready_for_draft(self, session: ExperienceIntakeSession) -> None:
        if not session.employer_name:
            msg = "Experience intake employer name is required before generating a draft."
            raise ValueError(msg)
        if not session.job_title:
            msg = "Experience intake job title is required before generating a draft."
            raise ValueError(msg)
        if not session.start_date:
            msg = "Experience intake start date is required before generating a draft."
            raise ValueError(msg)
        if not session.is_current_role and not session.end_date:
            msg = "Experience intake end date is required before generating a draft."
            raise ValueError(msg)
        if not session.source_text:
            msg = "Experience intake source text is required before generating a draft."
            raise ValueError(msg)
        if not session.follow_up_questions:
            msg = "Experience intake follow-up questions are required before generating a draft."
            raise ValueError(msg)
        if not session.user_answers:
            msg = "Experience intake answers are required before generating a draft."
            raise ValueError(msg)

    def _normalize_draft_role_details(
        self,
        session: ExperienceIntakeSession,
        draft: ExperienceEntry,
    ) -> ExperienceEntry:
        return draft.model_copy(
            update={
                "employer_name": session.employer_name,
                "job_title": session.job_title,
                "location": session.location,
                "employment_type": session.employment_type,
                "start_date": session.start_date,
                "end_date": session.end_date,
                "is_current_role": session.is_current_role,
            }
        )

    def _upsert_experience_entry(
        self,
        profile: CareerProfile,
        entry: ExperienceEntry,
    ) -> CareerProfile:
        entries = [existing for existing in profile.experience_entries if existing.id != entry.id]
        entries.append(entry)
        return profile.model_copy(update={"experience_entries": entries})

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    def _normalize_year_month(
        self,
        value: YearMonth | str | dict[str, int] | None,
        field_name: str,
    ) -> YearMonth | None:
        if value is None:
            return None

        try:
            return YearMonth.model_validate(value)
        except ValueError as exc:
            msg = f"Experience intake {field_name} must be a valid month/year value."
            raise ValueError(msg) from exc
