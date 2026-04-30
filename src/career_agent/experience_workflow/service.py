from __future__ import annotations

from career_agent.errors import NoUnanalyzedSourcesError, RoleNotFoundError
from career_agent.experience_roles.service import ExperienceRoleService
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    SourceQuestionGenerator,
)
from career_agent.role_sources.models import RoleSourceStatus
from career_agent.role_sources.service import RoleSourceService
from career_agent.source_analysis.models import SourceAnalysisRun
from career_agent.source_analysis.service import SourceAnalysisService


class ExperienceWorkflowService:
    """Orchestrates experience workflows across existing component services."""

    def __init__(
        self,
        role_service: ExperienceRoleService,
        source_service: RoleSourceService,
        analysis_service: SourceAnalysisService,
        question_generator: SourceQuestionGenerator | None = None,
    ) -> None:
        self.role_service = role_service
        self.source_service = source_service
        self.analysis_service = analysis_service
        self.question_generator = question_generator or DeterministicSourceQuestionGenerator()

    @property
    def question_generator_name(self) -> str:
        """Return the display name for the configured question generator."""

        return self.question_generator.generator_name

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
