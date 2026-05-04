from __future__ import annotations

import pytest

from career_agent.errors import (
    ActiveAnalysisRunExistsError,
    AnalysisRunNotFoundError,
    InvalidLLMOutputError,
    NoUnanalyzedSourcesError,
    OpenClarificationQuestionsError,
    SourceFindingsAlreadyExistError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
    FactChangeEvent,
    FactChangeEventType,
)
from career_agent.experience_facts.service import ExperienceFactService
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_roles.service import ExperienceRoleService
from career_agent.experience_workflow.finding_generator import GeneratedSourceFinding
from career_agent.experience_workflow.question_generator import GeneratedSourceQuestion
from career_agent.experience_workflow.service import (
    AppliedSourceFindingAction,
    ExperienceWorkflowService,
)
from career_agent.role_sources.models import RoleSourceEntry, RoleSourceStatus
from career_agent.role_sources.service import RoleSourceService
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFinding,
    SourceFindingStatus,
    SourceFindingType,
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


class FakeExperienceFactRepository:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}
        self.change_events: list[FactChangeEvent] = []

    def list(self, role_id: str | None = None) -> list[ExperienceFact]:
        facts = list(self.facts.values())
        if role_id is None:
            return facts
        return [fact for fact in facts if fact.role_id == role_id]

    def get(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact

    def list_change_events(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactChangeEvent]:
        events = self.change_events
        if fact_id is not None:
            events = [event for event in events if event.fact_id == fact_id]
        if role_id is not None:
            events = [event for event in events if event.role_id == role_id]
        return events

    def save_change_event(self, event: FactChangeEvent) -> None:
        self.change_events.append(event)


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


def build_fact(
    fact_id: str = "fact-1",
    role_id: str = "role-1",
    status: ExperienceFactStatus = ExperienceFactStatus.DRAFT,
) -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        source_ids=["source-1"],
        text="Led a reporting automation project.",
        status=status,
    )


def build_service() -> tuple[
    ExperienceWorkflowService,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
    FakeSourceAnalysisRepository,
    FakeExperienceFactRepository,
]:
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    analysis_repository = FakeSourceAnalysisRepository()
    fact_repository = FakeExperienceFactRepository()
    role_service = ExperienceRoleService(role_repository)
    source_service = RoleSourceService(source_repository, role_repository)
    analysis_service = SourceAnalysisService(
        analysis_repository,
        role_repository,
        source_repository,
        fact_repository,
    )
    fact_service = ExperienceFactService(
        fact_repository,
        role_repository,
        source_repository,
    )
    workflow_service = ExperienceWorkflowService(
        role_service,
        source_service,
        analysis_service,
        fact_service,
    )
    return (
        workflow_service,
        role_repository,
        source_repository,
        analysis_repository,
        fact_repository,
    )


def test_experience_workflow_analyzes_only_unanalyzed_sources() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    source_repository.save(build_source("source-2", status=RoleSourceStatus.ANALYZED))
    source_repository.save(build_source("source-3", status=RoleSourceStatus.ARCHIVED))

    run = service.analyze_sources("role-1")

    questions = analysis_repository.list_questions(run.id)
    assert service.question_generator_name == "deterministic"
    assert run.role_id == "role-1"
    assert run.source_ids == ["source-1"]
    assert len(questions) == 2
    assert questions[0].relevant_source_ids == ["source-1"]
    assert questions[0].question_text.startswith("DEV PLACEHOLDER:")
    assert "Senior Systems Analyst at Acme Analytics" in questions[0].question_text


def test_experience_workflow_does_not_mark_sources_analyzed() -> None:
    service, role_repository, source_repository, _analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))

    service.analyze_sources("role-1")

    assert source_repository.get("source-1").status == RoleSourceStatus.NOT_ANALYZED


def test_experience_workflow_rejects_role_without_unanalyzed_sources() -> None:
    service, role_repository, source_repository, _analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1", status=RoleSourceStatus.ANALYZED))

    with pytest.raises(NoUnanalyzedSourcesError, match="role-1"):
        service.analyze_sources("role-1")


def test_experience_workflow_rejects_when_active_run_exists_for_role() -> None:
    class FailingIfCalledQuestionGenerator:
        @property
        def generator_name(self) -> str:
            return "should-not-run"

        def generate_questions(self, role, sources):
            raise AssertionError("Question generator should not run when a role has an active run.")

    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    service.question_generator = FailingIfCalledQuestionGenerator()

    with pytest.raises(ActiveAnalysisRunExistsError, match="run-1"):
        service.analyze_sources("role-1")


def test_experience_workflow_uses_injected_question_generator() -> None:
    class FakeQuestionGenerator:
        @property
        def generator_name(self) -> str:
            return "fake"

        def generate_questions(self, role, sources):
            return [
                GeneratedSourceQuestion(
                    question_text=f"What should be clarified for {role.job_title}?",
                    relevant_source_ids=[source.id for source in sources],
                )
            ]

    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    analysis_repository = FakeSourceAnalysisRepository()
    fact_repository = FakeExperienceFactRepository()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    service = ExperienceWorkflowService(
        ExperienceRoleService(role_repository),
        RoleSourceService(source_repository, role_repository),
        SourceAnalysisService(
            analysis_repository,
            role_repository,
            source_repository,
            fact_repository,
        ),
        ExperienceFactService(fact_repository, role_repository, source_repository),
        question_generator=FakeQuestionGenerator(),
    )

    run = service.analyze_sources("role-1")

    questions = analysis_repository.list_questions(run.id)
    assert len(questions) == 1
    assert service.question_generator_name == "fake"
    assert questions[0].question_text == "What should be clarified for Senior Systems Analyst?"
    assert questions[0].relevant_source_ids == ["source-1"]


def test_experience_workflow_does_not_start_run_when_question_generation_fails() -> None:
    class FailingQuestionGenerator:
        @property
        def generator_name(self) -> str:
            return "failing"

        def generate_questions(self, role, sources):
            raise InvalidLLMOutputError("LLM response must be valid JSON.")

    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    analysis_repository = FakeSourceAnalysisRepository()
    fact_repository = FakeExperienceFactRepository()
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    service = ExperienceWorkflowService(
        ExperienceRoleService(role_repository),
        RoleSourceService(source_repository, role_repository),
        SourceAnalysisService(
            analysis_repository,
            role_repository,
            source_repository,
            fact_repository,
        ),
        ExperienceFactService(fact_repository, role_repository, source_repository),
        question_generator=FailingQuestionGenerator(),
    )

    with pytest.raises(InvalidLLMOutputError, match="valid JSON"):
        service.analyze_sources("role-1")

    assert analysis_repository.list_runs(role_id="role-1") == []


def test_experience_workflow_generates_findings_for_run_without_questions() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )

    findings = service.generate_findings("run-1")

    assert service.finding_generator_name == "deterministic"
    assert len(findings) == 1
    assert findings[0].analysis_run_id == "run-1"
    assert findings[0].source_id == "source-1"
    assert findings[0].finding_type == SourceFindingType.UNCLEAR
    assert analysis_repository.list_findings(analysis_run_id="run-1") == findings


def test_experience_workflow_generate_findings_uses_injected_generator_context() -> None:
    class FakeFindingGenerator:
        def __init__(self) -> None:
            self.received_context = None

        @property
        def generator_name(self) -> str:
            return "fake-finding"

        def generate_findings(self, role, sources, questions, messages, facts):
            self.received_context = {
                "role": role,
                "sources": sources,
                "questions": questions,
                "messages": messages,
                "facts": facts,
            }
            return [
                GeneratedSourceFinding(
                    source_id="source-1",
                    finding_type=SourceFindingType.SUPPORTS_FACT,
                    fact_id="fact-1",
                    rationale="The source directly supports the existing fact.",
                )
            ]

    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    generator = FakeFindingGenerator()
    service.finding_generator = generator
    role = build_role()
    role_repository.save(role)
    source = build_source("source-1")
    source_repository.save(source)
    fact = build_fact()
    fact_repository.save(fact)
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    question = SourceClarificationQuestion(
        id="question-1",
        analysis_run_id="run-1",
        question_text="What was the impact?",
        relevant_source_ids=["source-1"],
        status=SourceClarificationQuestionStatus.RESOLVED,
    )
    message = SourceClarificationMessage(
        id="message-1",
        question_id="question-1",
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly reporting time.",
    )
    analysis_repository.save_question(question)
    analysis_repository.save_message(message)

    findings = service.generate_findings("run-1")

    assert service.finding_generator_name == "fake-finding"
    assert findings[0].finding_type == SourceFindingType.SUPPORTS_FACT
    assert findings[0].fact_id == "fact-1"
    assert generator.received_context == {
        "role": role,
        "sources": [source],
        "questions": [question],
        "messages": [message],
        "facts": [fact],
    }


def test_experience_workflow_generate_findings_allows_skipped_questions() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    analysis_repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What was the impact?",
            status=SourceClarificationQuestionStatus.SKIPPED,
        )
    )

    findings = service.generate_findings("run-1")

    assert len(findings) == 1


def test_experience_workflow_generate_findings_rejects_missing_run() -> None:
    service, _role_repository, _source_repository, _analysis_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(AnalysisRunNotFoundError, match="run-1"):
        service.generate_findings("run-1")


def test_experience_workflow_generate_findings_rejects_open_questions() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    analysis_repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What was the impact?",
        )
    )

    with pytest.raises(OpenClarificationQuestionsError, match="question-1"):
        service.generate_findings("run-1")


def test_experience_workflow_generate_findings_rejects_existing_findings() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.UNCLEAR,
        )
    )

    with pytest.raises(SourceFindingsAlreadyExistError, match="run-1"):
        service.generate_findings("run-1")


def test_experience_workflow_generate_findings_rejects_missing_source() -> None:
    service, role_repository, _source_repository, analysis_repository, _fact_repository = (
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
        service.generate_findings("run-1")


def test_experience_workflow_generate_findings_rejects_source_role_mismatch() -> None:
    service, role_repository, source_repository, analysis_repository, _fact_repository = (
        build_service()
    )
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source("source-1", role_id="role-2"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )

    with pytest.raises(SourceRoleMismatchError, match="source-1"):
        service.generate_findings("run-1")


def test_experience_workflow_apply_findings_creates_draft_fact_from_new_fact() -> None:
    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    question = SourceClarificationQuestion(
        id="question-1",
        analysis_run_id="run-1",
        question_text="What was the impact?",
        relevant_source_ids=["source-1"],
        status=SourceClarificationQuestionStatus.RESOLVED,
    )
    message = SourceClarificationMessage(
        id="message-1",
        question_id="question-1",
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly reporting effort.",
    )
    finding = SourceFinding(
        id="finding-1",
        analysis_run_id="run-1",
        role_id="role-1",
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Reduced weekly reporting effort through automation.",
        rationale="The source and answer describe a distinct fact.",
        status=SourceFindingStatus.ACCEPTED,
    )
    analysis_repository.save_question(question)
    analysis_repository.save_message(message)
    analysis_repository.save_finding(finding)

    results = service.apply_findings("run-1")

    facts = fact_repository.list(role_id="role-1")
    applied_finding = analysis_repository.get_finding("finding-1")

    assert len(results) == 1
    assert results[0].action == AppliedSourceFindingAction.CREATED_FACT
    assert len(facts) == 1
    assert facts[0].status == ExperienceFactStatus.DRAFT
    assert facts[0].source_ids == ["source-1"]
    assert facts[0].question_ids == ["question-1"]
    assert facts[0].message_ids == ["message-1"]
    assert facts[0].text == "Reduced weekly reporting effort through automation."
    assert applied_finding.status == SourceFindingStatus.APPLIED
    assert applied_finding.applied_fact_id == facts[0].id
    assert fact_repository.change_events[-1].event_type == FactChangeEventType.CREATED
    assert fact_repository.change_events[-1].actor.value == "system"
    assert fact_repository.change_events[-1].source_message_ids == ["message-1"]
    assert "finding-1" in fact_repository.change_events[-1].summary


def test_experience_workflow_apply_findings_adds_supporting_evidence() -> None:
    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    source_repository.save(build_source("source-2"))
    fact_repository.save(
        build_fact(
            fact_id="fact-1",
            status=ExperienceFactStatus.ACTIVE,
        )
    )
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-2"],
        )
    )
    analysis_repository.save_question(
        SourceClarificationQuestion(
            id="question-1",
            analysis_run_id="run-1",
            question_text="What confirms the fact?",
            relevant_source_ids=["source-2"],
            status=SourceClarificationQuestionStatus.RESOLVED,
        )
    )
    analysis_repository.save_message(
        SourceClarificationMessage(
            id="message-1",
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text="The source describes the same automation project.",
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-2",
            fact_id="fact-1",
            finding_type=SourceFindingType.SUPPORTS_FACT,
            rationale="The source supports the existing fact.",
            status=SourceFindingStatus.ACCEPTED,
        )
    )

    results = service.apply_findings("run-1")

    fact = fact_repository.get("fact-1")
    applied_finding = analysis_repository.get_finding("finding-1")

    assert results[0].action == AppliedSourceFindingAction.ADDED_EVIDENCE
    assert fact.source_ids == ["source-1", "source-2"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact.status == ExperienceFactStatus.ACTIVE
    assert applied_finding.status == SourceFindingStatus.APPLIED
    assert applied_finding.applied_fact_id == "fact-1"
    assert fact_repository.change_events[-1].event_type == FactChangeEventType.EVIDENCE_ADDED


def test_experience_workflow_apply_findings_revises_active_fact_as_draft() -> None:
    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    source_repository.save(build_source("source-2"))
    fact_repository.save(
        build_fact(
            fact_id="fact-1",
            status=ExperienceFactStatus.ACTIVE,
        )
    )
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-2"],
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-2",
            fact_id="fact-1",
            finding_type=SourceFindingType.REVISES_FACT,
            proposed_fact_text="Led reporting automation that reduced weekly reporting effort.",
            rationale="The source adds supported impact detail.",
            status=SourceFindingStatus.ACCEPTED,
        )
    )

    results = service.apply_findings("run-1")

    draft_revisions = [
        fact
        for fact in fact_repository.list(role_id="role-1")
        if fact.supersedes_fact_id == "fact-1"
    ]
    applied_finding = analysis_repository.get_finding("finding-1")

    assert results[0].action == AppliedSourceFindingAction.REVISED_FACT
    assert len(draft_revisions) == 1
    assert draft_revisions[0].status == ExperienceFactStatus.DRAFT
    assert draft_revisions[0].source_ids == ["source-1", "source-2"]
    assert draft_revisions[0].text == (
        "Led reporting automation that reduced weekly reporting effort."
    )
    assert fact_repository.get("fact-1").status == ExperienceFactStatus.ACTIVE
    assert applied_finding.status == SourceFindingStatus.APPLIED
    assert applied_finding.applied_fact_id == draft_revisions[0].id
    assert FactChangeEventType.REVISED in {
        event.event_type for event in fact_repository.change_events
    }


def test_experience_workflow_apply_findings_skips_unapplied_artifact_types() -> None:
    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    fact_repository.save(build_fact(fact_id="fact-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.CONTRADICTS_FACT,
            status=SourceFindingStatus.ACCEPTED,
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-2",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.REVISES_FACT,
            status=SourceFindingStatus.ACCEPTED,
        )
    )

    results = service.apply_findings("run-1")

    assert [result.action for result in results] == [
        AppliedSourceFindingAction.SKIPPED,
        AppliedSourceFindingAction.SKIPPED,
    ]
    assert analysis_repository.get_finding("finding-1").status == SourceFindingStatus.ACCEPTED
    assert analysis_repository.get_finding("finding-2").status == SourceFindingStatus.ACCEPTED


def test_experience_workflow_apply_findings_ignores_already_applied_findings() -> None:
    service, role_repository, source_repository, analysis_repository, fact_repository = (
        build_service()
    )
    role_repository.save(build_role())
    source_repository.save(build_source("source-1"))
    fact_repository.save(build_fact(fact_id="fact-1"))
    analysis_repository.save_run(
        SourceAnalysisRun(
            id="run-1",
            role_id="role-1",
            source_ids=["source-1"],
        )
    )
    analysis_repository.save_finding(
        SourceFinding(
            id="finding-1",
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.SUPPORTS_FACT,
            status=SourceFindingStatus.APPLIED,
            applied_fact_id="fact-1",
        )
    )

    assert service.apply_findings("run-1") == []


def test_experience_workflow_apply_findings_rejects_missing_run() -> None:
    service, _role_repository, _source_repository, _analysis_repository, _fact_repository = (
        build_service()
    )

    with pytest.raises(AnalysisRunNotFoundError, match="run-1"):
        service.apply_findings("run-1")
