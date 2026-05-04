from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from career_agent.errors import (
    AnalysisRunNotFoundError,
    NoUnanalyzedSourcesError,
    OpenClarificationQuestionsError,
    RoleNotFoundError,
    SourceFindingsAlreadyExistError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
from career_agent.experience_facts.models import FactChangeActor
from career_agent.experience_facts.service import ExperienceFactService
from career_agent.experience_roles.service import ExperienceRoleService
from career_agent.experience_workflow.finding_generator import (
    DeterministicSourceFindingGenerator,
    SourceFindingGenerator,
)
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    SourceQuestionGenerator,
)
from career_agent.role_sources.models import RoleSourceStatus
from career_agent.role_sources.service import RoleSourceService
from career_agent.source_analysis.models import (
    SourceAnalysisRun,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFinding,
    SourceFindingStatus,
    SourceFindingType,
)
from career_agent.source_analysis.service import SourceAnalysisService


class AppliedSourceFindingAction(StrEnum):
    """Canonical action taken while applying a source finding."""

    CREATED_FACT = "created_fact"
    REVISED_FACT = "revised_fact"
    ADDED_EVIDENCE = "added_evidence"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class AppliedSourceFindingResult:
    """Result for one accepted source finding application attempt."""

    finding_id: str
    finding_type: SourceFindingType
    action: AppliedSourceFindingAction
    fact_id: str | None = None
    message: str | None = None


class ExperienceWorkflowService:
    """Orchestrates experience workflows across existing component services."""

    def __init__(
        self,
        role_service: ExperienceRoleService,
        source_service: RoleSourceService,
        analysis_service: SourceAnalysisService,
        fact_service: ExperienceFactService,
        question_generator: SourceQuestionGenerator | None = None,
        finding_generator: SourceFindingGenerator | None = None,
    ) -> None:
        self.role_service = role_service
        self.source_service = source_service
        self.analysis_service = analysis_service
        self.fact_service = fact_service
        self.question_generator = question_generator or DeterministicSourceQuestionGenerator()
        self.finding_generator = finding_generator or DeterministicSourceFindingGenerator()

    @property
    def question_generator_name(self) -> str:
        """Return the display name for the configured question generator."""

        return self.question_generator.generator_name

    @property
    def finding_generator_name(self) -> str:
        """Return the display name for the configured finding generator."""

        return self.finding_generator.generator_name

    def analyze_sources(self, role_id: str) -> SourceAnalysisRun:
        """Start source analysis for unanalyzed source entries on one role."""

        role = self.role_service.get_role(role_id)
        if role is None:
            msg = f"Experience role does not exist: {role_id}"
            raise RoleNotFoundError(msg)

        unanalyzed_sources = [
            source
            for source in self.source_service.list_sources(role_id=role_id)
            if source.status == RoleSourceStatus.NOT_ANALYZED
        ]
        if not unanalyzed_sources:
            msg = f"No unanalyzed sources found for role: {role_id}"
            raise NoUnanalyzedSourcesError(msg)

        self.analysis_service.ensure_no_active_run_for_role(role_id)
        generated_questions = self.question_generator.generate_questions(role, unanalyzed_sources)
        run = self.analysis_service.start_run(
            role_id=role_id,
            source_ids=[source.id for source in unanalyzed_sources],
        )
        for question in generated_questions:
            self.analysis_service.add_question(
                analysis_run_id=run.id,
                question_text=question.question_text,
                relevant_source_ids=question.relevant_source_ids,
            )
        return run

    def generate_findings(self, analysis_run_id: str) -> list[SourceFinding]:
        """Generate proposed source findings for a closed source analysis run."""

        run = self.analysis_service.get_run(analysis_run_id)
        if run is None:
            msg = f"Source analysis run does not exist: {analysis_run_id}"
            raise AnalysisRunNotFoundError(msg)

        existing_findings = self.analysis_service.list_findings(analysis_run_id=run.id)
        if existing_findings:
            msg = f"Source findings already exist for analysis run: {run.id}"
            raise SourceFindingsAlreadyExistError(msg)

        questions = self.analysis_service.list_questions(run.id)
        open_questions = [
            question
            for question in questions
            if question.status == SourceClarificationQuestionStatus.OPEN
        ]
        if open_questions:
            question_ids = ", ".join(question.id for question in open_questions)
            msg = f"Cannot generate findings while clarification questions are open: {question_ids}"
            raise OpenClarificationQuestionsError(msg)

        role = self.role_service.get_role(run.role_id)
        if role is None:
            msg = f"Experience role does not exist: {run.role_id}"
            raise RoleNotFoundError(msg)

        sources = []
        for source_id in run.source_ids:
            source = self.source_service.get_source(source_id)
            if source is None:
                msg = f"Role source does not exist: {source_id}"
                raise SourceNotFoundError(msg)
            if source.role_id != run.role_id:
                msg = f"Role source {source_id} does not belong to role: {run.role_id}"
                raise SourceRoleMismatchError(msg)
            sources.append(source)

        messages = [
            message
            for question in questions
            for message in self.analysis_service.list_messages(question.id)
        ]
        facts = self.fact_service.list_facts(role_id=run.role_id)
        generated_findings = self.finding_generator.generate_findings(
            role=role,
            sources=sources,
            questions=questions,
            messages=messages,
            facts=facts,
        )

        saved_findings = []
        for finding in generated_findings:
            saved_findings.append(
                self.analysis_service.add_finding(
                    analysis_run_id=run.id,
                    source_id=finding.source_id,
                    finding_type=finding.finding_type,
                    fact_id=finding.fact_id,
                    proposed_fact_text=finding.proposed_fact_text,
                    rationale=finding.rationale,
                )
            )
        return saved_findings

    def apply_findings(
        self,
        analysis_run_id: str,
        actor: FactChangeActor = FactChangeActor.SYSTEM,
    ) -> list[AppliedSourceFindingResult]:
        """Apply accepted source findings through deterministic fact services."""

        run = self.analysis_service.get_run(analysis_run_id)
        if run is None:
            msg = f"Source analysis run does not exist: {analysis_run_id}"
            raise AnalysisRunNotFoundError(msg)

        questions = self.analysis_service.list_questions(run.id)
        messages_by_question_id = {
            question.id: self.analysis_service.list_messages(question.id) for question in questions
        }
        accepted_findings = [
            finding
            for finding in self.analysis_service.list_findings(analysis_run_id=run.id)
            if finding.status == SourceFindingStatus.ACCEPTED
        ]

        results: list[AppliedSourceFindingResult] = []
        for finding in accepted_findings:
            question_ids, message_ids = self._evidence_ids_for_finding(
                finding=finding,
                questions=questions,
                messages_by_question_id=messages_by_question_id,
            )
            summary = self._finding_summary(finding)

            if finding.finding_type == SourceFindingType.NEW_FACT:
                fact = self.fact_service.add_fact(
                    role_id=finding.role_id,
                    text=finding.proposed_fact_text or "",
                    source_ids=[finding.source_id],
                    question_ids=question_ids,
                    message_ids=message_ids,
                    actor=actor,
                    summary=summary,
                    source_message_ids=message_ids,
                )
                applied_finding = self.analysis_service.apply_finding(
                    finding_id=finding.id,
                    applied_fact_id=fact.id,
                )
                results.append(
                    AppliedSourceFindingResult(
                        finding_id=applied_finding.id,
                        finding_type=applied_finding.finding_type,
                        action=AppliedSourceFindingAction.CREATED_FACT,
                        fact_id=fact.id,
                        message="Created draft experience fact.",
                    )
                )
                continue

            if finding.finding_type == SourceFindingType.REVISES_FACT:
                if finding.proposed_fact_text is None:
                    results.append(
                        AppliedSourceFindingResult(
                            finding_id=finding.id,
                            finding_type=finding.finding_type,
                            action=AppliedSourceFindingAction.SKIPPED,
                            fact_id=finding.fact_id,
                            message="revises_fact findings require proposed_fact_text to apply.",
                        )
                    )
                    continue

                fact = self.fact_service.revise_fact(
                    fact_id=finding.fact_id or "",
                    text=finding.proposed_fact_text,
                    source_ids=[finding.source_id],
                    question_ids=question_ids,
                    message_ids=message_ids,
                    actor=actor,
                    summary=summary,
                    source_message_ids=message_ids,
                )
                applied_finding = self.analysis_service.apply_finding(
                    finding_id=finding.id,
                    applied_fact_id=fact.id,
                )
                results.append(
                    AppliedSourceFindingResult(
                        finding_id=applied_finding.id,
                        finding_type=applied_finding.finding_type,
                        action=AppliedSourceFindingAction.REVISED_FACT,
                        fact_id=fact.id,
                        message="Created or updated draft fact revision.",
                    )
                )
                continue

            if finding.finding_type == SourceFindingType.SUPPORTS_FACT:
                fact = self.fact_service.add_evidence(
                    fact_id=finding.fact_id or "",
                    source_ids=[finding.source_id],
                    question_ids=question_ids,
                    message_ids=message_ids,
                    actor=actor,
                    summary=summary,
                    source_message_ids=message_ids,
                )
                applied_finding = self.analysis_service.apply_finding(
                    finding_id=finding.id,
                    applied_fact_id=fact.id,
                )
                results.append(
                    AppliedSourceFindingResult(
                        finding_id=applied_finding.id,
                        finding_type=applied_finding.finding_type,
                        action=AppliedSourceFindingAction.ADDED_EVIDENCE,
                        fact_id=fact.id,
                        message="Applied supporting evidence to fact.",
                    )
                )
                continue

            results.append(
                AppliedSourceFindingResult(
                    finding_id=finding.id,
                    finding_type=finding.finding_type,
                    action=AppliedSourceFindingAction.SKIPPED,
                    fact_id=finding.fact_id,
                    message=(
                        f"{finding.finding_type.value} findings are retained as "
                        "analysis artifacts and are not applied automatically."
                    ),
                )
            )

        return results

    def _evidence_ids_for_finding(
        self,
        finding: SourceFinding,
        questions: list[SourceClarificationQuestion],
        messages_by_question_id: dict[str, list[SourceClarificationMessage]],
    ) -> tuple[list[str], list[str]]:
        """Return conservative question/message evidence ids for one source finding."""

        question_ids = [
            question.id
            for question in questions
            if finding.source_id in question.relevant_source_ids
        ]
        message_ids = [
            message.id
            for question_id in question_ids
            for message in messages_by_question_id[question_id]
        ]
        return question_ids, message_ids

    def _finding_summary(self, finding: SourceFinding) -> str:
        """Build a fact change event summary from a source finding."""

        summary = f"Applied source finding {finding.id} ({finding.finding_type.value})."
        if finding.rationale is None:
            return summary
        return f"{summary} {finding.rationale}"
