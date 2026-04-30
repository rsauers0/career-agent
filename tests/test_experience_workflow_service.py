import pytest

from career_agent.errors import ActiveAnalysisRunExistsError, NoUnanalyzedSourcesError
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_workflow.service import ExperienceWorkflowService
from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus
from career_agent.role_sources.service import RoleSourceService
from career_agent.source_analysis.models import (
    SourceAnalysisRun,
    SourceClarificationQuestion,
)
from career_agent.source_analysis.service import SourceAnalysisService


class FakeExperienceRoleRepository:
    def __init__(self) -> None:
        self.roles: dict[str, ExperienceRole] = {}

    def get(self, role_id: str) -> ExperienceRole | None:
        return self.roles.get(role_id)

    def save(self, role: ExperienceRole) -> None:
        self.roles[role.id] = role


class FakeRoleSourceRepository:
    def __init__(self) -> None:
        self.sources: dict[str, RoleSourceEntry] = {}

    def list(self, role_id: str | None = None) -> list[RoleSourceEntry]:
        sources = list(self.sources.values())
        if role_id is None:
            return sources
        return [source for source in sources if source.role_id == role_id]

    def get(self, source_id: str) -> RoleSourceEntry | None:
        return self.sources.get(source_id)

    def save(self, source: RoleSourceEntry) -> None:
        self.sources[source.id] = source

    def delete(self, source_id: str) -> bool:
        if source_id not in self.sources:
            return False
        del self.sources[source_id]
        return True


class FakeSourceAnalysisRepository:
    def __init__(self) -> None:
        self.runs: dict[str, SourceAnalysisRun] = {}
        self.questions: dict[str, SourceClarificationQuestion] = {}

    def list_runs(self, role_id: str | None = None) -> list[SourceAnalysisRun]:
        runs = list(self.runs.values())
        if role_id is None:
            return runs
        return [run for run in runs if run.role_id == role_id]

    def get_run(self, run_id: str) -> SourceAnalysisRun | None:
        return self.runs.get(run_id)

    def save_run(self, run: SourceAnalysisRun) -> None:
        self.runs[run.id] = run

    def list_questions(self, analysis_run_id: str) -> list[SourceClarificationQuestion]:
        return [
            question
            for question in self.questions.values()
            if question.analysis_run_id == analysis_run_id
        ]

    def get_question(self, question_id: str) -> SourceClarificationQuestion | None:
        return self.questions.get(question_id)

    def save_question(self, question: SourceClarificationQuestion) -> None:
        self.questions[question.id] = question

    def list_messages(self, question_id: str):
        return []

    def save_message(self, message) -> None:
        raise NotImplementedError


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_source(
    source_id: str,
    *,
    role_id: str = "role-1",
    status: RoleSourceStatus = RoleSourceStatus.NOT_ANALYZED,
) -> RoleSourceEntry:
    return RoleSourceEntry(
        id=source_id,
        role_id=role_id,
        source_text="- Led a reporting automation project.",
        status=status,
    )


def build_service() -> tuple[
    ExperienceWorkflowService,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
    FakeSourceAnalysisRepository,
]:
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    analysis_repository = FakeSourceAnalysisRepository()
    source_service = RoleSourceService(source_repository, role_repository)
    analysis_service = SourceAnalysisService(
        analysis_repository,
        role_repository,
        source_repository,
    )
    workflow_service = ExperienceWorkflowService(source_service, analysis_service)
    return workflow_service, role_repository, source_repository, analysis_repository


def test_experience_workflow_analyzes_only_unanalyzed_sources() -> None:
    service, role_repository, source_repository, analysis_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    source_repository.save(build_source("source-2", status=RoleSourceStatus.ANALYZED))
    source_repository.save(build_source("source-3", status=RoleSourceStatus.ARCHIVED))

    run = service.analyze_sources("role-1")

    questions = analysis_repository.list_questions(run.id)
    assert run.role_id == "role-1"
    assert run.source_ids == ["source-1"]
    assert len(questions) == 2
    assert questions[0].relevant_source_ids == ["source-1"]
    assert questions[0].question_text.startswith("DEV PLACEHOLDER:")


def test_experience_workflow_does_not_mark_sources_analyzed() -> None:
    service, role_repository, source_repository, _analysis_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))

    service.analyze_sources("role-1")

    assert source_repository.get("source-1").status == RoleSourceStatus.NOT_ANALYZED


def test_experience_workflow_rejects_role_without_unanalyzed_sources() -> None:
    service, role_repository, source_repository, _analysis_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1", status=RoleSourceStatus.ANALYZED))

    with pytest.raises(NoUnanalyzedSourcesError, match="role-1"):
        service.analyze_sources("role-1")


def test_experience_workflow_rejects_when_active_run_exists_for_role() -> None:
    service, role_repository, source_repository, analysis_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )

    with pytest.raises(ActiveAnalysisRunExistsError, match="run-1"):
        service.analyze_sources("role-1")
