import pytest
from pydantic import ValidationError

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
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus
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
from career_agent.source_analysis.service import SourceAnalysisService


class FakeSourceAnalysisRepository:
    def __init__(self) -> None:
        self.runs: dict[str, SourceAnalysisRun] = {}
        self.questions: dict[str, SourceClarificationQuestion] = {}
        self.messages: dict[str, SourceClarificationMessage] = {}
        self.findings: dict[str, SourceFinding] = {}

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

    def list_findings(
        self,
        analysis_run_id: str | None = None,
        role_id: str | None = None,
        source_id: str | None = None,
        fact_id: str | None = None,
    ) -> list[SourceFinding]:
        findings = list(self.findings.values())
        if analysis_run_id is not None:
            findings = [
                finding for finding in findings if finding.analysis_run_id == analysis_run_id
            ]
        if role_id is not None:
            findings = [finding for finding in findings if finding.role_id == role_id]
        if source_id is not None:
            findings = [finding for finding in findings if finding.source_id == source_id]
        if fact_id is not None:
            findings = [finding for finding in findings if finding.fact_id == fact_id]
        return findings

    def get_finding(self, finding_id: str) -> SourceFinding | None:
        return self.findings.get(finding_id)

    def save_finding(self, finding: SourceFinding) -> None:
        self.findings[finding.id] = finding


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


class FakeExperienceFactRepository:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}

    def get(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact


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


def build_fact(fact_id: str = "fact-1", role_id: str = "role-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        source_ids=["source-1"],
        text="Led a reporting automation project.",
    )


def build_service() -> tuple[
    SourceAnalysisService,
    FakeSourceAnalysisRepository,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
    FakeExperienceFactRepository,
]:
    analysis_repository = FakeSourceAnalysisRepository()
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    fact_repository = FakeExperienceFactRepository()
    return (
        SourceAnalysisService(
            analysis_repository,
            role_repository,
            source_repository,
            fact_repository,
        ),
        analysis_repository,
        role_repository,
        source_repository,
        fact_repository,
    )


def test_source_analysis_service_starts_run_for_existing_role_and_sources() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))

    run = service.start_run(role_id="role-1", source_ids=["source-1", "source-2"])

    assert run.role_id == "role-1"
    assert run.source_ids == ["source-1", "source-2"]
    assert service.get_run(run.id) == run
    assert service.list_runs(role_id="role-1") == [run]


def test_source_analysis_service_rejects_second_active_run_for_same_role() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    active_run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(ActiveAnalysisRunExistsError, match=active_run.id):
        service.start_run(role_id="role-1", source_ids=["source-2"])


def test_source_analysis_service_allows_active_runs_for_different_roles() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role(role_id="role-1"))
    role_repository.save(build_role(role_id="role-2"))
    source_repository.save(build_source(source_id="source-1", role_id="role-1"))
    source_repository.save(build_source(source_id="source-2", role_id="role-2"))

    first_run = service.start_run(role_id="role-1", source_ids=["source-1"])
    second_run = service.start_run(role_id="role-2", source_ids=["source-2"])

    assert first_run.role_id == "role-1"
    assert second_run.role_id == "role-2"


def test_source_analysis_service_allows_new_run_after_prior_run_completed() -> None:
    service, analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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


def test_source_analysis_service_completes_run_and_marks_sources_analyzed() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    run = service.start_run(role_id="role-1", source_ids=["source-1", "source-2"])
    resolved_question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )
    skipped_question = service.add_question(
        analysis_run_id=run.id,
        question_text="Was this part of a larger modernization effort?",
    )
    service.resolve_question(resolved_question.id)
    service.skip_question(skipped_question.id)
    proposed_finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        finding_type=SourceFindingType.UNCLEAR,
        rationale="The source needs later semantic review.",
    )

    completed_run = service.complete_run(run.id)

    assert completed_run.status == SourceAnalysisStatus.COMPLETED
    assert completed_run.updated_at >= run.updated_at
    assert source_repository.get("source-1").status == RoleSourceStatus.ANALYZED
    assert source_repository.get("source-2").status == RoleSourceStatus.ANALYZED
    assert service.get_finding(proposed_finding.id) == proposed_finding


def test_source_analysis_service_rejects_complete_with_open_questions() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    question = service.add_question(
        analysis_run_id=run.id,
        question_text="What measurable impact did this automation have?",
    )

    with pytest.raises(OpenClarificationQuestionsError, match=question.id):
        service.complete_run(run.id)

    assert service.get_run(run.id).status == SourceAnalysisStatus.ACTIVE
    assert source_repository.get("source-1").status == RoleSourceStatus.NOT_ANALYZED


def test_source_analysis_service_rejects_complete_with_unapplied_accepted_findings() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Led reporting automation.",
    )
    accepted_finding = service.accept_finding(finding.id)

    with pytest.raises(UnappliedAcceptedSourceFindingsError, match=accepted_finding.id):
        service.complete_run(run.id)

    assert service.get_run(run.id).status == SourceAnalysisStatus.ACTIVE
    assert source_repository.get("source-1").status == RoleSourceStatus.NOT_ANALYZED


def test_source_analysis_service_archives_active_run_without_marking_sources_analyzed() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    archived_run = service.archive_run(run.id)
    new_run = service.start_run(role_id="role-1", source_ids=["source-2"])

    assert archived_run.status == SourceAnalysisStatus.ARCHIVED
    assert archived_run.updated_at >= run.updated_at
    assert source_repository.get("source-1").status == RoleSourceStatus.NOT_ANALYZED
    assert new_run.source_ids == ["source-2"]


def test_source_analysis_service_archives_completed_run() -> None:
    service, analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    completed_run = SourceAnalysisRun(
        id="run-1",
        role_id="role-1",
        source_ids=["source-1"],
        status=SourceAnalysisStatus.COMPLETED,
    )
    analysis_repository.save_run(completed_run)

    archived_run = service.archive_run("run-1")

    assert archived_run.status == SourceAnalysisStatus.ARCHIVED
    assert archived_run.updated_at >= completed_run.updated_at


def test_source_analysis_service_rejects_transition_from_archived_run() -> None:
    service, analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
            status=SourceAnalysisStatus.ARCHIVED,
        )
    )

    with pytest.raises(InvalidSourceAnalysisRunStatusTransitionError, match="run-1"):
        service.complete_run("run-1")

    with pytest.raises(InvalidSourceAnalysisRunStatusTransitionError, match="run-1"):
        service.archive_run("run-1")


def test_source_analysis_service_rejects_run_for_missing_role() -> None:
    service, _analysis_repository, _role_repository, source_repository, _fact_repository = (
        build_service()
    )
    source_repository.save(build_source())

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_rejects_run_without_sources() -> None:
    service, _analysis_repository, role_repository, _source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())

    with pytest.raises(ValidationError):
        service.start_run(role_id="role-1", source_ids=[])


def test_source_analysis_service_rejects_missing_source_id() -> None:
    service, _analysis_repository, role_repository, _source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())

    with pytest.raises(SourceNotFoundError, match="source-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_rejects_source_for_different_role() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source(source_id="source-1", role_id="role-2"))

    with pytest.raises(SourceRoleMismatchError, match="source-1"):
        service.start_run(role_id="role-1", source_ids=["source-1"])


def test_source_analysis_service_adds_question_to_existing_run() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, _role_repository, _source_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(AnalysisRunNotFoundError, match="run-1"):
        service.add_question(
            analysis_run_id="run-1",
            question_text="What measurable impact did this automation have?",
        )


def test_source_analysis_service_rejects_question_source_outside_run() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, _role_repository, _source_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.add_message(
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text="It reduced weekly reporting time.",
        )


def test_source_analysis_service_message_does_not_resolve_question() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
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
    service, _analysis_repository, _role_repository, _source_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.resolve_question("question-1")

    with pytest.raises(ClarificationQuestionNotFoundError, match="question-1"):
        service.skip_question("question-1")


def test_source_analysis_service_adds_new_fact_finding_for_run_source() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Led reporting automation for recurring team metrics.",
        rationale="The source describes a distinct automation responsibility.",
    )

    assert finding.analysis_run_id == run.id
    assert finding.role_id == "role-1"
    assert finding.source_id == "source-1"
    assert finding.fact_id is None
    assert finding.finding_type == SourceFindingType.NEW_FACT
    assert finding.status == SourceFindingStatus.PROPOSED
    assert service.list_findings(analysis_run_id=run.id) == [finding]


def test_source_analysis_service_adds_fact_comparison_finding() -> None:
    service, _analysis_repository, role_repository, source_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    fact_repository.save(build_fact())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        fact_id="fact-1",
        finding_type=SourceFindingType.SUPPORTS_FACT,
        rationale="The source directly supports the existing fact.",
    )

    assert finding.fact_id == "fact-1"
    assert service.get_finding(finding.id) == finding
    assert service.list_findings(fact_id="fact-1") == [finding]


def test_source_analysis_service_rejects_finding_for_missing_run() -> None:
    service, _analysis_repository, _role_repository, _source_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(AnalysisRunNotFoundError, match="run-1"):
        service.add_finding(
            analysis_run_id="run-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation.",
        )


def test_source_analysis_service_rejects_finding_source_outside_run() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(SourceNotInAnalysisRunError, match="source-2"):
        service.add_finding(
            analysis_run_id=run.id,
            source_id="source-2",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation.",
        )


def test_source_analysis_service_rejects_finding_for_missing_source_record() -> None:
    service, analysis_repository, role_repository, _source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )

    with pytest.raises(SourceNotFoundError, match="source-1"):
        service.add_finding(
            analysis_run_id="run-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation.",
        )


def test_source_analysis_service_rejects_finding_for_missing_fact() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(FactNotFoundError, match="fact-1"):
        service.add_finding(
            analysis_run_id=run.id,
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.SUPPORTS_FACT,
        )


def test_source_analysis_service_rejects_finding_for_fact_role_mismatch() -> None:
    service, _analysis_repository, role_repository, source_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source(role_id="role-1"))
    fact_repository.save(build_fact(fact_id="fact-1", role_id="role-2"))
    run = service.start_run(role_id="role-1", source_ids=["source-1"])

    with pytest.raises(FactRoleMismatchError, match="fact-1"):
        service.add_finding(
            analysis_run_id=run.id,
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.SUPPORTS_FACT,
        )


def test_source_analysis_service_updates_finding_status_explicitly() -> None:
    service, _analysis_repository, role_repository, source_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    fact_repository.save(build_fact())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Led reporting automation.",
    )

    accepted_finding = service.accept_finding(finding.id)
    applied_finding = service.apply_finding(accepted_finding.id, applied_fact_id="fact-1")
    archived_finding = service.archive_finding(applied_finding.id)

    assert accepted_finding.status == SourceFindingStatus.ACCEPTED
    assert accepted_finding.updated_at >= finding.updated_at
    assert applied_finding.status == SourceFindingStatus.APPLIED
    assert applied_finding.applied_fact_id == "fact-1"
    assert archived_finding.status == SourceFindingStatus.ARCHIVED
    assert archived_finding.applied_fact_id == "fact-1"


def test_source_analysis_service_rejects_invalid_finding_status_transition() -> None:
    service, _analysis_repository, role_repository, source_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source())
    run = service.start_run(role_id="role-1", source_ids=["source-1"])
    finding = service.add_finding(
        analysis_run_id=run.id,
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Led reporting automation.",
    )
    accepted_finding = service.accept_finding(finding.id)

    with pytest.raises(InvalidSourceFindingStatusTransitionError, match="Cannot transition"):
        service.reject_finding(accepted_finding.id)


def test_source_analysis_service_rejects_status_change_for_missing_finding() -> None:
    service, _analysis_repository, _role_repository, _source_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(SourceFindingNotFoundError, match="finding-1"):
        service.accept_finding("finding-1")
