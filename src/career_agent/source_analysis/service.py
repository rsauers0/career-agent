from __future__ import annotations

from datetime import UTC, datetime

from career_agent.errors import (
    ActiveAnalysisRunExistsError,
    AnalysisRunNotFoundError,
    ClarificationQuestionNotFoundError,
    FactNotFoundError,
    FactRoleMismatchError,
    InvalidSourceAnalysisRunStatusTransitionError,
    InvalidSourceFindingStatusTransitionError,
    OpenClarificationQuestionsError,
    RoleNotFoundError,
    SourceFindingNotFoundError,
    SourceNotFoundError,
    SourceNotInAnalysisRunError,
    SourceRoleMismatchError,
    UnappliedAcceptedSourceFindingsError,
)
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.models import RoleSourceStatus
from career_agent.role_sources.repository import RoleSourceRepository
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceAnalysisStatus,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFinding,
    SourceFindingStatus,
    SourceFindingType,
)
from career_agent.source_analysis.repository import SourceAnalysisRepository

ALLOWED_FINDING_STATUS_TRANSITIONS: dict[
    SourceFindingStatus,
    set[SourceFindingStatus],
] = {
    SourceFindingStatus.PROPOSED: {
        SourceFindingStatus.ACCEPTED,
        SourceFindingStatus.REJECTED,
        SourceFindingStatus.ARCHIVED,
    },
    SourceFindingStatus.ACCEPTED: {
        SourceFindingStatus.APPLIED,
        SourceFindingStatus.ARCHIVED,
    },
    SourceFindingStatus.APPLIED: {SourceFindingStatus.ARCHIVED},
    SourceFindingStatus.REJECTED: {SourceFindingStatus.ARCHIVED},
    SourceFindingStatus.ARCHIVED: set(),
}

ALLOWED_RUN_STATUS_TRANSITIONS: dict[
    SourceAnalysisStatus,
    set[SourceAnalysisStatus],
] = {
    SourceAnalysisStatus.ACTIVE: {
        SourceAnalysisStatus.COMPLETED,
        SourceAnalysisStatus.ARCHIVED,
    },
    SourceAnalysisStatus.COMPLETED: {SourceAnalysisStatus.ARCHIVED},
    SourceAnalysisStatus.ARCHIVED: set(),
}


class SourceAnalysisService:
    """Application behavior for source analysis workflow artifacts."""

    def __init__(
        self,
        analysis_repository: SourceAnalysisRepository,
        role_repository: ExperienceRoleRepository,
        source_repository: RoleSourceRepository,
        fact_repository: ExperienceFactRepository,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.role_repository = role_repository
        self.source_repository = source_repository
        self.fact_repository = fact_repository

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

    def list_findings(
        self,
        analysis_run_id: str | None = None,
        role_id: str | None = None,
        source_id: str | None = None,
        fact_id: str | None = None,
    ) -> list[SourceFinding]:
        """Return source findings, optionally filtered by relationship ids."""

        return self.analysis_repository.list_findings(
            analysis_run_id=analysis_run_id,
            role_id=role_id,
            source_id=source_id,
            fact_id=fact_id,
        )

    def get_finding(self, finding_id: str) -> SourceFinding | None:
        """Return one source finding if it exists."""

        return self.analysis_repository.get_finding(finding_id)

    def start_run(self, role_id: str, source_ids: list[str]) -> SourceAnalysisRun:
        """Create a source analysis run for an existing role and valid sources."""

        self.ensure_no_active_run_for_role(role_id)
        self._validate_role_and_sources(role_id=role_id, source_ids=source_ids)
        run = SourceAnalysisRun(role_id=role_id, source_ids=source_ids)
        self.analysis_repository.save_run(run)
        return run

    def complete_run(self, analysis_run_id: str) -> SourceAnalysisRun:
        """Complete an analysis run and mark included role sources analyzed."""

        run = self._get_required_run(analysis_run_id)
        self._validate_run_transition(
            run=run,
            status=SourceAnalysisStatus.COMPLETED,
        )
        self._validate_run_completion(run)
        updated_run = run.model_copy(
            update={
                "status": SourceAnalysisStatus.COMPLETED,
                "updated_at": datetime.now(UTC),
            }
        )
        self.analysis_repository.save_run(updated_run)
        self._mark_run_sources_analyzed(updated_run)
        return updated_run

    def archive_run(self, analysis_run_id: str) -> SourceAnalysisRun:
        """Archive an active or completed analysis run."""

        run = self._get_required_run(analysis_run_id)
        self._validate_run_transition(
            run=run,
            status=SourceAnalysisStatus.ARCHIVED,
        )
        updated_run = run.model_copy(
            update={
                "status": SourceAnalysisStatus.ARCHIVED,
                "updated_at": datetime.now(UTC),
            }
        )
        self.analysis_repository.save_run(updated_run)
        return updated_run

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

    def add_finding(
        self,
        analysis_run_id: str,
        source_id: str,
        finding_type: SourceFindingType,
        fact_id: str | None = None,
        proposed_fact_text: str | None = None,
        rationale: str | None = None,
    ) -> SourceFinding:
        """Create a structured finding for an existing source analysis run."""

        run = self._get_required_run(analysis_run_id)
        self._validate_finding_source(run=run, source_id=source_id)
        if fact_id is not None:
            self._validate_finding_fact(role_id=run.role_id, fact_id=fact_id)
        finding = SourceFinding(
            analysis_run_id=analysis_run_id,
            role_id=run.role_id,
            source_id=source_id,
            fact_id=fact_id,
            finding_type=finding_type,
            proposed_fact_text=proposed_fact_text,
            rationale=rationale,
        )
        self.analysis_repository.save_finding(finding)
        return finding

    def accept_finding(self, finding_id: str) -> SourceFinding:
        """Accept a proposed source finding without mutating canonical facts."""

        return self._set_finding_status(
            finding_id=finding_id,
            status=SourceFindingStatus.ACCEPTED,
        )

    def reject_finding(self, finding_id: str) -> SourceFinding:
        """Reject a proposed source finding without mutating canonical facts."""

        return self._set_finding_status(
            finding_id=finding_id,
            status=SourceFindingStatus.REJECTED,
        )

    def archive_finding(self, finding_id: str) -> SourceFinding:
        """Archive a source finding."""

        return self._set_finding_status(
            finding_id=finding_id,
            status=SourceFindingStatus.ARCHIVED,
        )

    def apply_finding(self, finding_id: str, applied_fact_id: str) -> SourceFinding:
        """Mark an accepted source finding as applied to a canonical fact."""

        finding = self._get_required_finding(finding_id)
        self._validate_finding_fact(role_id=finding.role_id, fact_id=applied_fact_id)
        return self._set_finding_status(
            finding_id=finding_id,
            status=SourceFindingStatus.APPLIED,
            applied_fact_id=applied_fact_id,
        )

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

    def ensure_no_active_run_for_role(self, role_id: str) -> None:
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

    def _validate_run_transition(
        self,
        run: SourceAnalysisRun,
        status: SourceAnalysisStatus,
    ) -> None:
        """Validate source analysis run lifecycle transitions."""

        allowed_statuses = ALLOWED_RUN_STATUS_TRANSITIONS[run.status]
        if status not in allowed_statuses:
            msg = (
                f"Cannot transition source analysis run {run.id} "
                f"from {run.status.value} to {status.value}."
            )
            raise InvalidSourceAnalysisRunStatusTransitionError(msg)

    def _validate_run_completion(self, run: SourceAnalysisRun) -> None:
        """Validate that an active analysis run is settled enough to complete."""

        open_questions = [
            question
            for question in self.analysis_repository.list_questions(run.id)
            if question.status == SourceClarificationQuestionStatus.OPEN
        ]
        if open_questions:
            question_ids = ", ".join(question.id for question in open_questions)
            msg = (
                "Cannot complete source analysis run while clarification questions "
                f"are open: {question_ids}"
            )
            raise OpenClarificationQuestionsError(msg)

        unapplied_findings = [
            finding
            for finding in self.analysis_repository.list_findings(analysis_run_id=run.id)
            if finding.status == SourceFindingStatus.ACCEPTED and finding.applied_fact_id is None
        ]
        if unapplied_findings:
            finding_ids = ", ".join(finding.id for finding in unapplied_findings)
            msg = (
                "Cannot complete source analysis run with accepted findings that "
                f"have not been applied: {finding_ids}"
            )
            raise UnappliedAcceptedSourceFindingsError(msg)

        self._validate_role_and_sources(role_id=run.role_id, source_ids=run.source_ids)

    def _mark_run_sources_analyzed(self, run: SourceAnalysisRun) -> None:
        """Mark all sources included in a completed analysis run as analyzed."""

        for source_id in run.source_ids:
            source = self.source_repository.get(source_id)
            if source is None:
                msg = f"Role source does not exist: {source_id}"
                raise SourceNotFoundError(msg)
            if source.role_id != run.role_id:
                msg = f"Role source {source_id} does not belong to role: {run.role_id}"
                raise SourceRoleMismatchError(msg)
            self.source_repository.save(
                source.model_copy(update={"status": RoleSourceStatus.ANALYZED})
            )

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

    def _get_required_finding(self, finding_id: str) -> SourceFinding:
        """Return one source finding or raise an application-level error."""

        finding = self.analysis_repository.get_finding(finding_id)
        if finding is None:
            msg = f"Source finding does not exist: {finding_id}"
            raise SourceFindingNotFoundError(msg)
        return finding

    def _validate_finding_source(self, run: SourceAnalysisRun, source_id: str) -> None:
        """Validate that a finding source exists and is included in the run."""

        self._validate_relevant_sources(run=run, relevant_source_ids=[source_id])
        source = self.source_repository.get(source_id)
        if source is None:
            msg = f"Role source does not exist: {source_id}"
            raise SourceNotFoundError(msg)
        if source.role_id != run.role_id:
            msg = f"Role source {source_id} does not belong to role: {run.role_id}"
            raise SourceRoleMismatchError(msg)

    def _validate_finding_fact(self, role_id: str, fact_id: str) -> None:
        """Validate that an optional referenced fact exists and belongs to the role."""

        fact = self.fact_repository.get(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)
        if fact.role_id != role_id:
            msg = f"Experience fact {fact_id} does not belong to role: {role_id}"
            raise FactRoleMismatchError(msg)

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

    def _set_finding_status(
        self,
        finding_id: str,
        status: SourceFindingStatus,
        applied_fact_id: str | None = None,
    ) -> SourceFinding:
        """Persist an explicit source finding status transition."""

        finding = self._get_required_finding(finding_id)
        allowed_statuses = ALLOWED_FINDING_STATUS_TRANSITIONS[finding.status]
        if status not in allowed_statuses:
            msg = (
                f"Cannot transition source finding {finding.id} "
                f"from {finding.status.value} to {status.value}."
            )
            raise InvalidSourceFindingStatusTransitionError(msg)

        update_values = {
            "status": status,
            "updated_at": datetime.now(UTC),
        }
        if applied_fact_id is not None:
            update_values["applied_fact_id"] = applied_fact_id

        updated_finding = finding.model_copy(update=update_values)
        self.analysis_repository.save_finding(updated_finding)
        return updated_finding
