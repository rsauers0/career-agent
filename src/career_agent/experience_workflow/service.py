from __future__ import annotations

from career_agent.errors import NoUnanalyzedSourcesError
from career_agent.role_sources.models import RoleSourceStatus
from career_agent.role_sources.service import RoleSourceService
from career_agent.source_analysis.models import SourceAnalysisRun
from career_agent.source_analysis.service import SourceAnalysisService


class ExperienceWorkflowService:
    """Orchestrates experience workflows across existing component services."""

    def __init__(
        self,
        source_service: RoleSourceService,
        analysis_service: SourceAnalysisService,
    ) -> None:
        self.source_service = source_service
        self.analysis_service = analysis_service

    def analyze_sources(self, role_id: str) -> SourceAnalysisRun:
        """Start source analysis for unanalyzed source entries on one role."""

        unanalyzed_sources = [
            source
            for source in self.source_service.list_sources(role_id=role_id)
            if source.status == RoleSourceStatus.NOT_ANALYZED
        ]
        if not unanalyzed_sources:
            msg = f"No unanalyzed sources found for role: {role_id}"
            raise NoUnanalyzedSourcesError(msg)

        run = self.analysis_service.start_run(
            role_id=role_id,
            source_ids=[source.id for source in unanalyzed_sources],
        )
        self.analysis_service.add_question(
            analysis_run_id=run.id,
            question_text=(
                "DEV PLACEHOLDER: What measurable impact, outcome, or business value "
                "should be clarified from this source material?"
            ),
            relevant_source_ids=run.source_ids,
        )
        self.analysis_service.add_question(
            analysis_run_id=run.id,
            question_text=(
                "DEV PLACEHOLDER: Are there tools, technologies, stakeholders, "
                "or scope details that should be captured before bullet generation?"
            ),
            relevant_source_ids=run.source_ids,
        )
        return run
