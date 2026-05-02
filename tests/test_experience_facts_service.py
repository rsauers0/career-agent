from __future__ import annotations

import pytest

from career_agent.errors import (
    EvidenceReferenceRemovalError,
    FactNotFoundError,
    FactRevisionNotAllowedError,
    FactRoleMismatchError,
    InvalidFactStatusTransitionError,
    RoleNotFoundError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
    FactChangeActor,
    FactChangeEvent,
    FactChangeEventType,
)
from career_agent.experience_facts.service import ExperienceFactService
from career_agent.experience_roles.models import ExperienceRole
from career_agent.role_sources.models import RoleSourceEntry


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

    def delete(self, fact_id: str) -> bool:
        if fact_id not in self.facts:
            return False
        del self.facts[fact_id]
        return True


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
    ExperienceFactService,
    FakeExperienceFactRepository,
    FakeExperienceRoleRepository,
    FakeRoleSourceRepository,
]:
    fact_repository = FakeExperienceFactRepository()
    role_repository = FakeExperienceRoleRepository()
    source_repository = FakeRoleSourceRepository()
    return (
        ExperienceFactService(
            fact_repository,
            role_repository,
            source_repository,
        ),
        fact_repository,
        role_repository,
        source_repository,
    )


def test_experience_fact_service_lists_facts() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    first_fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
        source_ids=["source-1"],
    )
    second_fact = service.add_fact(
        role_id="role-1",
        text="Built a dashboard for service performance trends.",
    )

    assert service.list_facts() == [first_fact, second_fact]
    assert service.list_facts(role_id="role-1") == [first_fact, second_fact]


def test_experience_fact_service_returns_fact_by_id() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    assert service.get_fact(fact.id) == fact
    assert service.get_fact("missing-fact") is None


def test_experience_fact_service_lists_change_events() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    events = service.list_change_events(fact_id=fact.id)

    assert len(events) == 1
    assert events[0].event_type == FactChangeEventType.CREATED
    assert service.list_change_events(role_id="role-1") == events


def test_experience_fact_service_adds_fact_for_existing_role() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())

    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
        details=["Reduced monthly reconciliation effort."],
        systems=["Power Platform"],
        skills=["Power Automate"],
        functions=["workflow automation"],
    )

    assert fact.role_id == "role-1"
    assert fact.source_ids == ["source-1"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact.text == "Automated reporting workflows."
    assert fact.details == ["Reduced monthly reconciliation effort."]
    assert fact.systems == ["Power Platform"]
    assert fact.skills == ["Power Automate"]
    assert fact.functions == ["workflow automation"]
    assert fact.status == ExperienceFactStatus.DRAFT
    assert _fact_repository.change_events[0].event_type == FactChangeEventType.CREATED
    assert _fact_repository.change_events[0].actor == FactChangeActor.USER
    assert _fact_repository.change_events[0].fact_id == fact.id
    assert _fact_repository.change_events[0].to_status == ExperienceFactStatus.DRAFT


def test_experience_fact_service_adds_fact_that_supersedes_existing_fact() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    prior_fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    fact = service.add_fact(
        role_id="role-1",
        text="Automated monthly reporting workflows.",
        supersedes_fact_id=prior_fact.id,
    )

    assert fact.supersedes_fact_id == prior_fact.id


def test_experience_fact_service_rejects_missing_superseded_fact() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    with pytest.raises(FactNotFoundError, match="missing-fact"):
        service.add_fact(
            role_id="role-1",
            text="Automated reporting workflows.",
            supersedes_fact_id="missing-fact",
        )


def test_experience_fact_service_rejects_superseded_fact_for_different_role() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role(role_id="role-1"))
    role_repository.save(build_role(role_id="role-2"))
    prior_fact = service.add_fact(
        role_id="role-2",
        text="Built a service trend dashboard.",
    )

    with pytest.raises(FactRoleMismatchError, match=prior_fact.id):
        service.add_fact(
            role_id="role-1",
            text="Automated reporting workflows.",
            supersedes_fact_id=prior_fact.id,
        )


def test_experience_fact_service_rejects_fact_for_missing_role() -> None:
    service, _fact_repository, _role_repository, _source_repository = build_service()

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.add_fact(
            role_id="role-1",
            text="Automated reporting workflows.",
        )


def test_experience_fact_service_rejects_missing_source_id() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())

    with pytest.raises(SourceNotFoundError, match="source-1"):
        service.add_fact(
            role_id="role-1",
            text="Automated reporting workflows.",
            source_ids=["source-1"],
        )


def test_experience_fact_service_rejects_source_for_different_role() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role(role_id="role-1"))
    source_repository.save(build_source(source_id="source-1", role_id="role-2"))

    with pytest.raises(SourceRoleMismatchError, match="source-1"):
        service.add_fact(
            role_id="role-1",
            text="Automated reporting workflows.",
            source_ids=["source-1"],
        )


def test_experience_fact_service_saves_existing_fact_with_validation() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source())
    fact = ExperienceFact(
        id="fact-1",
        role_id="role-1",
        source_ids=["source-1"],
        text="Automated reporting workflows.",
        status=ExperienceFactStatus.ACTIVE,
    )

    service.save_fact(fact)

    assert service.get_fact("fact-1") == fact


def test_experience_fact_service_allows_adding_evidence_references() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    source_repository.save(build_source(source_id="source-2"))
    fact = service.add_fact(
        role_id="role-1",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
        text="Automated reporting workflows.",
    )
    updated_fact = fact.model_copy(
        update={
            "source_ids": ["source-1", "source-2"],
            "question_ids": ["question-1", "question-2"],
            "message_ids": ["message-1", "message-2"],
        }
    )

    service.save_fact(updated_fact)

    assert service.get_fact(fact.id) == updated_fact


def test_experience_fact_service_save_rejects_invalid_status_transition() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    active_fact = service.activate_fact(fact.id)
    invalid_fact = active_fact.model_copy(update={"status": ExperienceFactStatus.REJECTED})

    with pytest.raises(InvalidFactStatusTransitionError, match="active -> rejected"):
        service.save_fact(invalid_fact)


def test_experience_fact_service_save_rejects_active_content_revision() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    active_fact = service.activate_fact(fact.id)
    invalid_fact = active_fact.model_copy(update={"text": "Automated monthly reporting workflows."})

    with pytest.raises(FactRevisionNotAllowedError, match="active"):
        service.save_fact(invalid_fact)


def test_experience_fact_service_rejects_removed_evidence_references() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    fact = service.add_fact(
        role_id="role-1",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
        text="Automated reporting workflows.",
    )
    updated_fact = fact.model_copy(
        update={
            "source_ids": [],
            "question_ids": ["question-1"],
            "message_ids": ["message-1"],
        }
    )

    with pytest.raises(EvidenceReferenceRemovalError, match="source_ids=source-1"):
        service.save_fact(updated_fact)


def test_experience_fact_service_activates_draft_fact() -> None:
    service, fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    activated_fact = service.activate_fact(fact.id)

    assert activated_fact.status == ExperienceFactStatus.ACTIVE
    assert service.get_fact(fact.id) == activated_fact
    assert fact_repository.change_events[-1].event_type == FactChangeEventType.ACTIVATED
    assert fact_repository.change_events[-1].from_status == ExperienceFactStatus.DRAFT
    assert fact_repository.change_events[-1].to_status == ExperienceFactStatus.ACTIVE


def test_experience_fact_service_rejects_invalid_transition() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    active_fact = service.activate_fact(fact.id)

    with pytest.raises(InvalidFactStatusTransitionError, match="active -> rejected"):
        service.reject_fact(active_fact.id)


def test_experience_fact_service_marks_needs_clarification_and_returns_to_draft() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    needs_clarification_fact = service.mark_needs_clarification(fact.id)
    draft_fact = service.return_to_draft(fact.id)

    assert needs_clarification_fact.status == ExperienceFactStatus.NEEDS_CLARIFICATION
    assert draft_fact.status == ExperienceFactStatus.DRAFT


def test_experience_fact_service_rejects_and_archives_fact() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    rejected_fact = service.reject_fact(fact.id)

    archived_fact = service.archive_fact(rejected_fact.id)

    assert rejected_fact.status == ExperienceFactStatus.REJECTED
    assert archived_fact.status == ExperienceFactStatus.ARCHIVED


def test_experience_fact_service_revises_draft_fact_in_place() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    revised_fact = service.revise_fact(
        fact_id=fact.id,
        text="Automated monthly reporting workflows.",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
        details=["Reduced monthly reconciliation effort."],
        systems=["Power Platform"],
        skills=["Power Automate"],
        functions=["workflow automation"],
    )

    assert revised_fact.id == fact.id
    assert revised_fact.status == ExperienceFactStatus.DRAFT
    assert revised_fact.text == "Automated monthly reporting workflows."
    assert revised_fact.source_ids == ["source-1"]
    assert revised_fact.question_ids == ["question-1"]
    assert revised_fact.message_ids == ["message-1"]
    assert revised_fact.details == ["Reduced monthly reconciliation effort."]
    assert revised_fact.systems == ["Power Platform"]
    assert revised_fact.skills == ["Power Automate"]
    assert revised_fact.functions == ["workflow automation"]


def test_experience_fact_service_revises_active_fact_as_new_draft() -> None:
    service, _fact_repository, role_repository, source_repository = build_service()
    role_repository.save(build_role())
    source_repository.save(build_source(source_id="source-1"))
    fact = service.add_fact(
        role_id="role-1",
        source_ids=["source-1"],
        text="Automated reporting workflows.",
    )
    active_fact = service.activate_fact(fact.id)

    revised_fact = service.revise_fact(
        fact_id=active_fact.id,
        text="Automated monthly reporting workflows.",
        question_ids=["question-1"],
    )

    assert revised_fact.id != active_fact.id
    assert revised_fact.status == ExperienceFactStatus.DRAFT
    assert revised_fact.supersedes_fact_id == active_fact.id
    assert revised_fact.source_ids == ["source-1"]
    assert revised_fact.question_ids == ["question-1"]
    assert service.get_fact(active_fact.id).status == ExperienceFactStatus.ACTIVE


def test_experience_fact_service_activation_supersedes_prior_active_fact() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    active_fact = service.activate_fact(fact.id)
    revised_fact = service.revise_fact(
        fact_id=active_fact.id,
        text="Automated monthly reporting workflows.",
    )

    activated_revision = service.activate_fact(revised_fact.id)
    superseded_fact = service.get_fact(active_fact.id)

    assert activated_revision.status == ExperienceFactStatus.ACTIVE
    assert superseded_fact.status == ExperienceFactStatus.SUPERSEDED
    assert superseded_fact.superseded_by_fact_id == activated_revision.id


def test_experience_fact_service_rejects_revision_for_terminal_status() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )
    rejected_fact = service.reject_fact(fact.id)

    with pytest.raises(FactRevisionNotAllowedError, match="rejected"):
        service.revise_fact(
            fact_id=rejected_fact.id,
            text="Automated monthly reporting workflows.",
        )


def test_experience_fact_service_deletes_fact() -> None:
    service, _fact_repository, role_repository, _source_repository = build_service()
    role_repository.save(build_role())
    fact = service.add_fact(
        role_id="role-1",
        text="Automated reporting workflows.",
    )

    assert service.delete_fact(fact.id) is True
    assert service.delete_fact("missing-fact") is False
    assert service.get_fact(fact.id) is None
