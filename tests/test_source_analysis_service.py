import pytest
from pydantic import ValidationError

from career_agent.errors import (
    ActiveAnalysisRunExistsError,
    AnalysisRunNotFoundError,
    ClarificationQuestionNotFoundError,
    RoleNotFoundError,
    SourceNotFoundError,
    SourceNotInAnalysisRunError,
    SourceRoleMismatchError,
)
from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceAnalysisStatus,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
)
from career_agent.source_analysis.service import SourceAnalysisService


class FakeSourceAnalysisRepository:
    def __init__(self) -> None:
        self.runs: dict[str, SourceAnalysisRun] = {}
        self.questions: dict[str, SourceClarificationQuestion] = {}
        self.messages: dict[str, SourceClarificationMessage] = {}

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

    def list_messages(self, question_id: str) -> list[SourceClarificationMessage]:
        return [message for message in self.messages.values() if message.question_id == question_id]

    def get_message(self, message_id: str) -> SourceClarificationMessage | None:
        return self.messages.get(message_id)

    def save_message(self, message: SourceClarificationMessage) -> None:
        self.messages[message.id] = message


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

    def get(self, source_id: str) -> RoleSourceEntry | None:
        return self.sources.get(source_id)

    def save(self, source: RoleSourceEntry) -> None:
        self.sources[source.id] = source


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_source(source_id: str = "source-1", role_id: str = "role-1") -> RoleSourceEntry:
    return RoleSourceEntry(
        id=source_id,
        role_id=role_id,
        source_text="- Led a reporting automation project.",
    )


def build_service() -> tuple[
    SourceAnalysisService,
    FakeSourceAnalysisRepository,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
]:
    analysis_repository = FakeSourceAnalysisRepository()
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    return (
        SourceAnalysisService(
            analysis_repository,
            role_repository,
            source_repository,
        ),
        analysis_repository,
        role_repository,
        source_repository,
    )


def test_source_analysis_service_starts_run_for_existing_role_and_sources() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))

    run = service.start_run(role_id="role-1", source_ids=["source-1", "source-2"])

    assert run.role_id == "role-1"
    assert run.source_ids == ["source-1", "source-2"]
    assert service.get_run(run.id) == run
    assert service.list_runs(role_id="role-1") == [run]


def test_source_analysis_service_rejects_second_active_run_for_same_role() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    active_run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(ActiveAnalysisRunExistsError, match=active_run.id):
        service.start_run(role_id="role-1", source_ids=["source-2"])


def test_source_analysis_service_allows_active_runs_for_different_roles() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role(role_id="role-1"))
    role_repository.save(build_role(role_id="role-2"))
    source_repository.save(build_source(source_id="source-1", role_id="role-1"))
    source_repository.save(build_source(source_id="source-2", role_id="role-2"))

    first_run = service.start_run(role_id="role-1", source_ids=["source-1"])
    second_run = service.start_run(role_id="role-2", source_ids=["source-2"])

    assert first_run.role_id == "role-1"
    assert second_run.role_id == "role-2"


def test_source_analysis_service_allows_new_run_after_prior_run_completed() -> None:
    service, analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
            status=SourceAnalysisStatus.COMPLETED,
        )
    )

    run = service.start_run(role_id="role-1", source_ids=["source-2"])

    assert run.role_id == "role-1"
    assert run.source_ids == ["source-2"]


def test_source_analysis_service_rejects_run_for_missing_role() -> None:
    service, _analysis_repository, _role_repository, source_repository = build_service()
    source_repository.save(build_source())

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_rejects_run_without_sources() -> None:
    service, _analysis_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    with pytest.raises(ValidationError):
        service.start_run(role_id="role-1", source_ids=[])


def test_source_analysis_service_rejects_missing_source_id() -> None:
    service, _analysis_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    with pytest.raises(SourceNotFoundError, match="source-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_rejects_source_for_different_role() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source(source_id="source-1", role_id="role-2"))

    with pytest.raises(SourceRoleMismatchError, match="source-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_adds_question_to_existing_run() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
        relevant_source_ids=["source-1"],
    )

    assert question.analysis_run_id == run.id
    assert question.relevant_source_ids == ["source-1"]
    assert question.status == SourceClarificationQuestionStatus.OPEN
    assert service.list_questions(run.id) == [question]


def test_source_analysis_service_rejects_question_for_missing_run() -> None:
    service, _analysis_repository, _role_repository, _source_repository = build_service()

    with pytest.raises(AnalysisRunNotFoundError, match="run-1"):
        service.add_question(
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )


def test_source_analysis_service_rejects_question_source_outside_run() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(SourceNotInAnalysisRunError, match="source-2"):
        service.add_question(
            analysis_run_id=run.id,
            question_text="What measurable impact did this automation have?",
            relevant_source_ids=["source-2"],
        )


def test_source_analysis_service_adds_message_to_existing_question() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )

    message = service.add_message(
        question_id=question.id,
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly reporting time from 6 hours to 2.",
    )

    assert message.question_id == question.id
    assert message.author == ClarificationMessageAuthor.USER
    assert service.list_messages(question.id) == [message]


def test_source_analysis_service_rejects_message_for_missing_question() -> None:
    service, _analysis_repository, _role_repository, _source_repository = build_service()

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.add_message(
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text="It reduced weekly reporting time.",
        )


def test_source_analysis_service_message_does_not_resolve_question() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )

    service.add_message(
        question_id=question.id,
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly reporting time.",
    )

    assert service.list_questions(run.id)[0].status == SourceClarificationQuestionStatus.OPEN


def test_source_analysis_service_resolves_question_explicitly() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )

    resolved_question = service.resolve_question(question.id)

    assert resolved_question.status == SourceClarificationQuestionStatus.RESOLVED
    assert resolved_question.updated_at >= question.updated_at
    assert service.list_questions(run.id) == [resolved_question]


def test_source_analysis_service_skips_question_explicitly() -> None:
    service, _analysis_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )

    skipped_question = service.skip_question(question.id)

    assert skipped_question.status == SourceClarificationQuestionStatus.SKIPPED
    assert skipped_question.updated_at >= question.updated_at
    assert service.list_questions(run.id) == [skipped_question]


def test_source_analysis_service_rejects_status_change_for_missing_question() -> None:
    service, _analysis_repository, _role_repository, _source_repository = build_service()

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.resolve_question("question-1")

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.skip_question("question-1")
