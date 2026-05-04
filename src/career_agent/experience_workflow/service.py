from __future__ import annotations

from career_agent.errors import (
    AnalysisRunNotFoundError,
    NoUnanalyzedSourcesError,
    OpenClarificationQuestionsError,
    RoleNotFoundError,
    SourceFindingsAlreadyExistError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
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
    SourceClarificationQuestionStatus,
    SourceFinding,
)
from career_agent.source_analysis.service import SourceAnalysisService


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
