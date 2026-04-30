from __future__ import annotations

from datetime import UTC, datetime

from career_agent.errors import (
    ActiveAnalysisRunExistsError,
    AnalysisRunNotFoundError,
    ClarificationQuestionNotFoundError,
    RoleNotFoundError,
    SourceNotFoundError,
    SourceNotInAnalysisRunError,
    SourceRoleMismatchError,
)
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.repository import RoleSourceRepository
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceAnalysisStatus,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
)
from career_agent.source_analysis.repository import SourceAnalysisRepository


class SourceAnalysisService:
    """Application behavior for source analysis workflow artifacts."""

    def __init__(
        self,
        analysis_repository: SourceAnalysisRepository,
        role_repository: ExperienceRoleRepository,
        source_repository: RoleSourceRepository,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.role_repository = role_repository
        self.source_repository = source_repository

    def list_runs(self, role_id: str | None = None) -> list[SourceAnalysisRun]:
        """Return source analysis runs, optionally filtered by role id."""

        return self.analysis_repository.list_runs(role_id=role_id)

    def get_run(self, analysis_run_id: str) -> SourceAnalysisRun | None:
        """Return one source analysis run if it exists."""

        return self.analysis_repository.get_run(analysis_run_id)

    def list_questions(self, analysis_run_id: str) -> list[SourceClarificationQuestion]:
        """Return clarification questions for one analysis run."""

        return self.analysis_repository.list_questions(analysis_run_id)

    def list_messages(self, question_id: str) -> list[SourceClarificationMessage]:
        """Return clarification messages for one question."""

        return self.analysis_repository.list_messages(question_id)

    def start_run(self, role_id: str, source_ids: list[str]) -> SourceAnalysisRun:
        """Create a source analysis run for an existing role and valid sources."""

        self._validate_no_active_run_for_role(role_id)
        self._validate_role_and_sources(role_id=role_id, source_ids=source_ids)
        run = SourceAnalysisRun(role_id=role_id, source_ids=source_ids)
        self.analysis_repository.save_run(run)
        return run

    def add_question(
        self,
        analysis_run_id: str,
        question_text: str,
        relevant_source_ids: list[str] | None = None,
    ) -> SourceClarificationQuestion:
        """Create a clarification question for an existing source analysis run."""

        run = self._get_required_run(analysis_run_id)
        self._validate_relevant_sources(
            run=run,
            relevant_source_ids=relevant_source_ids or [],
        )
        question = SourceClarificationQuestion(
            analysis_run_id=analysis_run_id,
            question_text=question_text,
            relevant_source_ids=relevant_source_ids or [],
        )
        self.analysis_repository.save_question(question)
        return question

    def add_message(
        self,
        question_id: str,
        author: ClarificationMessageAuthor,
        message_text: str,
    ) -> SourceClarificationMessage:
        """Append one message to an existing clarification question."""

        self._get_required_question(question_id)
        message = SourceClarificationMessage(
            question_id=question_id,
            author=author,
            message_text=message_text,
        )
        self.analysis_repository.save_message(message)
        return message

    def resolve_question(self, question_id: str) -> SourceClarificationQuestion:
        """Mark a clarification question as resolved after explicit approval."""

        return self._set_question_status(
            question_id=question_id,
            status=SourceClarificationQuestionStatus.RESOLVED,
        )

    def skip_question(self, question_id: str) -> SourceClarificationQuestion:
        """Mark a clarification question as skipped after explicit approval."""

        return self._set_question_status(
            question_id=question_id,
            status=SourceClarificationQuestionStatus.SKIPPED,
        )

    def _validate_no_active_run_for_role(self, role_id: str) -> None:
        """Validate that a role does not already have an active analysis run."""

        for run in self.analysis_repository.list_runs(role_id=role_id):
            if run.status == SourceAnalysisStatus.ACTIVE:
                msg = f"Active source analysis run already exists for role {role_id}: {run.id}"
                raise ActiveAnalysisRunExistsError(msg)

    def _validate_role_and_sources(self, role_id: str, source_ids: list[str]) -> None:
        """Validate that role and source references are internally consistent."""

        if self.role_repository.get(role_id) is None:
            msg = f"Experience role does not exist: {role_id}"
            raise RoleNotFoundError(msg)

        for source_id in source_ids:
            source = self.source_repository.get(source_id)
            if source is None:
                msg = f"Role source does not exist: {source_id}"
                raise SourceNotFoundError(msg)
            if source.role_id != role_id:
                msg = f"Role source {source_id} does not belong to role: {role_id}"
                raise SourceRoleMismatchError(msg)

    def _validate_relevant_sources(
        self,
        run: SourceAnalysisRun,
        relevant_source_ids: list[str],
    ) -> None:
        """Validate that relevant source ids are included in the analysis run."""

        run_source_ids = set(run.source_ids)
        for source_id in relevant_source_ids:
            if source_id not in run_source_ids:
                msg = f"Source {source_id} is not part of analysis run: {run.id}"
                raise SourceNotInAnalysisRunError(msg)

    def _get_required_run(self, analysis_run_id: str) -> SourceAnalysisRun:
        """Return one run or raise an application-level error."""

        run = self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            msg = f"Source analysis run does not exist: {analysis_run_id}"
            raise AnalysisRunNotFoundError(msg)
        return run

    def _get_required_question(self, question_id: str) -> SourceClarificationQuestion:
        """Return one clarification question or raise an application-level error."""

        question = self.analysis_repository.get_question(question_id)
        if question is None:
            msg = f"Clarification question does not exist: {question_id}"
            raise ClarificationQuestionNotFoundError(msg)
        return question

    def _set_question_status(
        self,
        question_id: str,
        status: SourceClarificationQuestionStatus,
    ) -> SourceClarificationQuestion:
        """Persist an explicit clarification question status transition."""

        question = self._get_required_question(question_id)
        updated_question = question.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.analysis_repository.save_question(updated_question)
        return updated_question
