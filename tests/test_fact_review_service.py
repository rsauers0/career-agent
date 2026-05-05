import pytest

from career_agent.errors import (
    ActiveFactReviewThreadExistsError,
    FactNotFoundError,
    FactReviewActionNotFoundError,
    FactReviewActionsAlreadyExistError,
    FactReviewThreadNotFoundError,
    InvalidFactReviewActionStatusTransitionError,
    InvalidFactReviewThreadStatusTransitionError,
    InvalidLLMOutputError,
    RoleNotFoundError,
)
from career_agent.experience_facts.models import (
    ExperienceFact,
    ExperienceFactStatus,
    FactChangeActor,
)
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.action_generator import (
    GeneratedFactReviewAction,
)
from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewActionStatus,
    FactReviewActionType,
    FactReviewMessage,
    FactReviewMessageAuthor,
    FactReviewRecommendedAction,
    FactReviewThread,
    FactReviewThreadStatus,
)
from career_agent.fact_review.service import FactReviewService
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
    ScopedConstraintStatus,
)
from career_agent.workflow_approval import (
    WorkflowApprovalRequest,
    WorkflowApprovalResult,
    WorkflowApprovalStatus,
)


class FakeFactReviewRepository:
    def __init__(self) -> None:
        self.threads: dict[str, FactReviewThread] = {}
        self.messages: dict[str, FactReviewMessage] = {}
        self.actions: dict[str, FactReviewAction] = {}

    def list_threads(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewThread]:
        threads = list(self.threads.values())
        if fact_id is not None:
            threads = [thread for thread in threads if thread.fact_id == fact_id]
        if role_id is not None:
            threads = [thread for thread in threads if thread.role_id == role_id]
        return threads

    def get_thread(self, thread_id: str) -> FactReviewThread | None:
        return self.threads.get(thread_id)

    def save_thread(self, thread: FactReviewThread) -> None:
        self.threads[thread.id] = thread

    def list_messages(self, thread_id: str) -> list[FactReviewMessage]:
        return [message for message in self.messages.values() if message.thread_id == thread_id]

    def save_message(self, message: FactReviewMessage) -> None:
        self.messages[message.id] = message

    def list_actions(
        self,
        thread_id: str | None = None,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewAction]:
        actions = list(self.actions.values())
        if thread_id is not None:
            actions = [action for action in actions if action.thread_id == thread_id]
        if fact_id is not None:
            actions = [action for action in actions if action.fact_id == fact_id]
        if role_id is not None:
            actions = [action for action in actions if action.role_id == role_id]
        return actions

    def get_action(self, action_id: str) -> FactReviewAction | None:
        return self.actions.get(action_id)

    def save_action(self, action: FactReviewAction) -> None:
        self.actions[action.id] = action


class FakeExperienceFactService:
    def __init__(self) -> None:
        self.facts: dict[str, ExperienceFact] = {}
        self.calls: list[tuple[str, FactChangeActor, str | None, list[str]]] = []

    def get_fact(self, fact_id: str) -> ExperienceFact | None:
        return self.facts.get(fact_id)

    def save(self, fact: ExperienceFact) -> None:
        self.facts[fact.id] = fact

    def activate_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(update={"status": ExperienceFactStatus.ACTIVE})
        self.save(updated_fact)
        self.calls.append(("activate_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def reject_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(update={"status": ExperienceFactStatus.REJECTED})
        self.save(updated_fact)
        self.calls.append(("reject_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def revise_fact(
        self,
        fact_id: str,
        text: str,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        details: list[str] | None = None,
        systems: list[str] | None = None,
        skills: list[str] | None = None,
        functions: list[str] | None = None,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(
            update={
                "text": text,
                "source_ids": [*fact.source_ids, *(source_ids or [])],
                "question_ids": [*fact.question_ids, *(question_ids or [])],
                "message_ids": [*fact.message_ids, *(message_ids or [])],
            }
        )
        self.save(updated_fact)
        self.calls.append(("revise_fact", actor, summary, source_message_ids or []))
        return updated_fact

    def add_evidence(
        self,
        fact_id: str,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        fact = self._get_required_fact(fact_id)
        updated_fact = fact.model_copy(
            update={
                "source_ids": [*fact.source_ids, *(source_ids or [])],
                "question_ids": [*fact.question_ids, *(question_ids or [])],
                "message_ids": [*fact.message_ids, *(message_ids or [])],
            }
        )
        self.save(updated_fact)
        self.calls.append(("add_evidence", actor, summary, source_message_ids or []))
        return updated_fact

    def _get_required_fact(self, fact_id: str) -> ExperienceFact:
        fact = self.get_fact(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)
        return fact


class FakeExperienceRoleService:
    def __init__(self) -> None:
        self.roles: dict[str, ExperienceRole] = {}

    def get_role(self, role_id: str) -> ExperienceRole | None:
        return self.roles.get(role_id)

    def save(self, role: ExperienceRole) -> None:
        self.roles[role.id] = role


class FakeScopedConstraintService:
    def __init__(self) -> None:
        self.constraints: dict[str, ScopedConstraint] = {}
        self.applicable_constraints: list[ScopedConstraint] = []

    def add_constraint(
        self,
        scope_type: ConstraintScopeType,
        constraint_type: ConstraintType,
        rule_text: str,
        scope_id: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ScopedConstraint:
        constraint = ScopedConstraint(
            scope_type=scope_type,
            scope_id=scope_id,
            constraint_type=constraint_type,
            rule_text=rule_text,
            source_message_ids=source_message_ids or [],
        )
        self.constraints[constraint.id] = constraint
        return constraint

    def list_applicable_constraints(
        self,
        role_id: str | None = None,
        fact_id: str | None = None,
    ) -> list[ScopedConstraint]:
        return [
            constraint
            for constraint in self.applicable_constraints
            if constraint.status == ScopedConstraintStatus.ACTIVE
        ]


class FakeFactReviewActionGenerator:
    generator_name = "fake"

    def __init__(self, generated_actions: list[GeneratedFactReviewAction]) -> None:
        self.generated_actions = generated_actions
        self.calls: list[
            tuple[
                ExperienceRole,
                ExperienceFact,
                FactReviewThread,
                list[FactReviewMessage],
                list[FactReviewAction],
                list[ScopedConstraint],
            ]
        ] = []

    def generate_actions(
        self,
        role: ExperienceRole,
        fact: ExperienceFact,
        thread: FactReviewThread,
        messages: list[FactReviewMessage],
        existing_actions: list[FactReviewAction],
        constraints: list[ScopedConstraint],
    ) -> list[GeneratedFactReviewAction]:
        self.calls.append((role, fact, thread, messages, existing_actions, constraints))
        return self.generated_actions


class FakeWorkflowApprovalService:
    def __init__(self, result: WorkflowApprovalResult) -> None:
        self.result = result
        self.requests: list[WorkflowApprovalRequest] = []

    def request_approval(self, request: WorkflowApprovalRequest) -> WorkflowApprovalResult:
        self.requests.append(request)
        return self.result


def build_fact(fact_id: str = "fact-1", role_id: str = "role-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id=role_id,
        text="Automated reporting workflows.",
    )


def build_role(role_id: str = "role-1") -> ExperienceRole:
    return ExperienceRole(
        id=role_id,
        employer_name="Acme Analytics",
        job_title="Systems Analyst",
        start_date="01/2020",
        end_date="02/2024",
    )


def build_service() -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceFactService,
]:
    review_repository = FakeFactReviewRepository()
    role_service = FakeExperienceRoleService()
    fact_service = FakeExperienceFactService()
    constraint_service = FakeScopedConstraintService()
    return (
        FactReviewService(review_repository, role_service, fact_service, constraint_service),
        review_repository,
        fact_service,
    )


def build_service_with_constraint_service() -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceFactService,
    FakeScopedConstraintService,
]:
    review_repository = FakeFactReviewRepository()
    role_service = FakeExperienceRoleService()
    fact_service = FakeExperienceFactService()
    constraint_service = FakeScopedConstraintService()
    return (
        FactReviewService(review_repository, role_service, fact_service, constraint_service),
        review_repository,
        fact_service,
        constraint_service,
    )


def build_service_with_generation(
    generated_actions: list[GeneratedFactReviewAction],
) -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceRoleService,
    FakeExperienceFactService,
    FakeScopedConstraintService,
    FakeFactReviewActionGenerator,
]:
    review_repository = FakeFactReviewRepository()
    role_service = FakeExperienceRoleService()
    fact_service = FakeExperienceFactService()
    constraint_service = FakeScopedConstraintService()
    action_generator = FakeFactReviewActionGenerator(generated_actions)
    return (
        FactReviewService(
            review_repository,
            role_service,
            fact_service,
            constraint_service,
            action_generator,
        ),
        review_repository,
        role_service,
        fact_service,
        constraint_service,
        action_generator,
    )


def build_service_with_approval(
    approval_service: FakeWorkflowApprovalService,
) -> tuple[
    FactReviewService,
    FakeFactReviewRepository,
    FakeExperienceFactService,
    FakeWorkflowApprovalService,
]:
    review_repository = FakeFactReviewRepository()
    role_service = FakeExperienceRoleService()
    fact_service = FakeExperienceFactService()
    constraint_service = FakeScopedConstraintService()
    return (
        FactReviewService(
            review_repository,
            role_service,
            fact_service,
            constraint_service,
            approval_service=approval_service,
        ),
        review_repository,
        fact_service,
        approval_service,
    )


def test_fact_review_service_starts_thread_for_existing_fact() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())

    thread = service.start_thread("fact-1")

    assert thread.fact_id == "fact-1"
    assert thread.role_id == "role-1"
    assert thread.status == FactReviewThreadStatus.OPEN
    assert review_repository.get_thread(thread.id) == thread


def test_fact_review_service_rejects_missing_fact() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactNotFoundError, match="fact-1"):
        service.start_thread("fact-1")


def test_fact_review_service_rejects_second_open_thread_for_fact() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    first_thread = service.start_thread("fact-1")

    with pytest.raises(ActiveFactReviewThreadExistsError, match=first_thread.id):
        service.start_thread("fact-1")


def test_fact_review_service_allows_new_thread_after_resolve() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    first_thread = service.start_thread("fact-1")
    service.resolve_thread(first_thread.id)

    second_thread = service.start_thread("fact-1")

    assert second_thread.id != first_thread.id
    assert second_thread.status == FactReviewThreadStatus.OPEN


def test_fact_review_service_lists_threads() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact(fact_id="fact-1", role_id="role-1"))
    fact_service.save(build_fact(fact_id="fact-2", role_id="role-2"))
    first_thread = service.start_thread("fact-1")
    second_thread = service.start_thread("fact-2")

    assert service.list_threads() == [first_thread, second_thread]
    assert service.list_threads(fact_id="fact-1") == [first_thread]
    assert service.list_threads(role_id="role-2") == [second_thread]


def test_fact_review_service_adds_message_to_thread() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    message = service.add_message(
        thread_id=thread.id,
        author=FactReviewMessageAuthor.USER,
        message_text="Please split this into two facts.",
        recommended_action=FactReviewRecommendedAction.SPLIT_FACT,
    )

    assert message.thread_id == thread.id
    assert message.author == FactReviewMessageAuthor.USER
    assert message.message_text == "Please split this into two facts."
    assert message.recommended_action == FactReviewRecommendedAction.SPLIT_FACT
    assert service.list_messages(thread.id) == [message]


def test_fact_review_service_rejects_message_for_missing_thread() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.add_message(
            thread_id="thread-1",
            author=FactReviewMessageAuthor.USER,
            message_text="Looks good.",
        )


def test_fact_review_service_resolves_and_archives_thread() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    resolved_thread = service.resolve_thread(thread.id)
    archived_thread = service.archive_thread(resolved_thread.id)

    assert resolved_thread.status == FactReviewThreadStatus.RESOLVED
    assert archived_thread.status == FactReviewThreadStatus.ARCHIVED
    assert review_repository.get_thread(thread.id) == archived_thread


def test_fact_review_service_rejects_invalid_status_transition() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    archived_thread = service.archive_thread(thread.id)

    with pytest.raises(InvalidFactReviewThreadStatusTransitionError, match="archived"):
        service.resolve_thread(archived_thread.id)


def test_fact_review_service_rejects_status_change_for_missing_thread() -> None:
    service, _review_repository, _fact_repository = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.resolve_thread("thread-1")


def test_fact_review_service_adds_action_from_thread_context() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REVISE_FACT,
        rationale="User clarified the wording.",
        source_message_ids=["message-1"],
        revised_text="Managed reporting workflows.",
    )

    assert action.thread_id == thread.id
    assert action.fact_id == "fact-1"
    assert action.role_id == "role-1"
    assert action.status == FactReviewActionStatus.PROPOSED
    assert action.rationale == "User clarified the wording."
    assert service.list_actions(thread_id=thread.id) == [action]


def test_fact_review_service_rejects_action_for_missing_thread() -> None:
    service, _review_repository, _fact_service = build_service()

    with pytest.raises(FactReviewThreadNotFoundError, match="thread-1"):
        service.add_action(
            thread_id="thread-1",
            action_type=FactReviewActionType.ACTIVATE_FACT,
        )


def test_fact_review_service_generates_actions_from_thread_context() -> None:
    (
        service,
        review_repository,
        role_service,
        fact_service,
        constraint_service,
        action_generator,
    ) = build_service_with_generation(
        [
            GeneratedFactReviewAction(
                action_type=FactReviewActionType.REVISE_FACT,
                rationale="User supplied clearer wording.",
                source_message_ids=["review-message-1"],
                revised_text="Managed reporting workflows for leadership review.",
            )
        ]
    )
    role = build_role()
    fact = build_fact()
    role_service.save(role)
    fact_service.save(fact)
    constraint = ScopedConstraint(
        id="constraint-1",
        scope_type=ConstraintScopeType.FACT,
        scope_id="fact-1",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not imply enterprise-wide scope.",
        status=ScopedConstraintStatus.ACTIVE,
    )
    constraint_service.applicable_constraints = [constraint]
    thread = service.start_thread("fact-1")
    message = FactReviewMessage(
        id="review-message-1",
        thread_id=thread.id,
        author=FactReviewMessageAuthor.USER,
        message_text="Please make the scope clearer.",
    )
    review_repository.save_message(message)

    actions = service.generate_actions(thread.id)

    assert len(actions) == 1
    assert actions[0].action_type == FactReviewActionType.REVISE_FACT
    assert actions[0].status == FactReviewActionStatus.PROPOSED
    assert actions[0].fact_id == "fact-1"
    assert actions[0].role_id == "role-1"
    assert actions[0].source_message_ids == ["review-message-1"]
    assert actions[0].revised_text == "Managed reporting workflows for leadership review."
    assert review_repository.get_action(actions[0].id) == actions[0]
    assert len(action_generator.calls) == 1
    call = action_generator.calls[0]
    assert call[0] == role
    assert call[1] == fact
    assert call[2] == thread
    assert call[3] == [message]
    assert call[4] == []
    assert call[5] == [constraint]


def test_fact_review_service_generate_actions_allows_empty_generator_output() -> None:
    service, _review_repository, role_service, fact_service, _constraint_service, _generator = (
        build_service_with_generation([])
    )
    role_service.save(build_role())
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    assert service.generate_actions(thread.id) == []


def test_fact_review_service_generate_actions_rejects_existing_proposed_actions() -> None:
    service, _review_repository, role_service, fact_service, _constraint_service, _generator = (
        build_service_with_generation([])
    )
    role_service.save(build_role())
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )

    with pytest.raises(FactReviewActionsAlreadyExistError, match=action.id):
        service.generate_actions(thread.id)


def test_fact_review_service_generate_actions_rejects_missing_role() -> None:
    service, _review_repository, _role_service, fact_service, _constraint_service, _generator = (
        build_service_with_generation([])
    )
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    with pytest.raises(RoleNotFoundError, match="role-1"):
        service.generate_actions(thread.id)


def test_fact_review_service_generate_actions_rejects_unknown_review_message_id() -> None:
    service, _review_repository, role_service, fact_service, _constraint_service, _generator = (
        build_service_with_generation(
            [
                GeneratedFactReviewAction(
                    action_type=FactReviewActionType.ACTIVATE_FACT,
                    source_message_ids=["missing-message"],
                )
            ]
        )
    )
    role_service.save(build_role())
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")

    with pytest.raises(InvalidLLMOutputError, match="missing-message"):
        service.generate_actions(thread.id)


def test_fact_review_service_applies_activate_action() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
        rationale="Fact is supported.",
        source_message_ids=["review-message-1"],
    )

    applied_action = service.apply_action(action.id, actor=FactChangeActor.LLM)

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert applied_action.applied_fact_id == "fact-1"
    assert review_repository.get_action(action.id) == applied_action
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.ACTIVE
    assert fact_service.calls == [
        (
            "activate_fact",
            FactChangeActor.LLM,
            "Fact is supported.",
            ["review-message-1"],
        )
    ]


def test_fact_review_service_requests_approval_before_activation() -> None:
    approval_service = FakeWorkflowApprovalService(
        WorkflowApprovalResult(
            status=WorkflowApprovalStatus.APPROVED,
            rationale="Approved by test approval service.",
        )
    )
    service, _review_repository, fact_service, approval_service = build_service_with_approval(
        approval_service
    )
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
        rationale="User confirmed this fact is ready.",
        source_message_ids=["review-message-1"],
    )

    applied_action = service.apply_action(action.id, actor=FactChangeActor.LLM)

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert applied_action.applied_fact_id == "fact-1"
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.ACTIVE
    assert len(approval_service.requests) == 1
    request = approval_service.requests[0]
    assert request.request_type.value == "fact_activation"
    assert request.subject_id == "fact-1"
    assert request.role_id == "role-1"
    assert request.rationale == "User confirmed this fact is ready."
    assert request.source_message_ids == ["review-message-1"]


def test_fact_review_service_rejects_activate_action_when_approval_rejects() -> None:
    approval_service = FakeWorkflowApprovalService(
        WorkflowApprovalResult(
            status=WorkflowApprovalStatus.REJECTED,
            rationale="Activation requires another human review.",
        )
    )
    service, review_repository, fact_service, _approval_service = build_service_with_approval(
        approval_service
    )
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
        rationale="User confirmed this fact is ready.",
        source_message_ids=["review-message-1"],
    )

    rejected_action = service.apply_action(action.id, actor=FactChangeActor.LLM)

    assert rejected_action.status == FactReviewActionStatus.REJECTED
    assert rejected_action.applied_fact_id is None
    assert rejected_action.rationale == (
        "User confirmed this fact is ready.\n\n"
        "Approval rejected: Activation requires another human review."
    )
    assert review_repository.get_action(action.id) == rejected_action
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.DRAFT
    assert fact_service.calls == []


def test_fact_review_service_applies_reject_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REJECT_FACT,
    )

    applied_action = service.apply_action(action.id)

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact_service.get_fact("fact-1").status == ExperienceFactStatus.REJECTED
    assert fact_service.calls[-1][0] == "reject_fact"


def test_fact_review_service_applies_revise_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.REVISE_FACT,
        revised_text="Managed Power Platform reporting workflows.",
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
    )

    applied_action = service.apply_action(action.id)
    fact = fact_service.get_fact("fact-1")

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact.text == "Managed Power Platform reporting workflows."
    assert fact.source_ids == ["source-1"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact_service.calls[-1][0] == "revise_fact"


def test_fact_review_service_applies_add_evidence_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ADD_EVIDENCE,
        source_ids=["source-1"],
        question_ids=["question-1"],
        message_ids=["message-1"],
    )

    applied_action = service.apply_action(action.id)
    fact = fact_service.get_fact("fact-1")

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert fact.source_ids == ["source-1"]
    assert fact.question_ids == ["question-1"]
    assert fact.message_ids == ["message-1"]
    assert fact_service.calls[-1][0] == "add_evidence"


def test_fact_review_service_applies_propose_constraint_action() -> None:
    service, review_repository, fact_service, constraint_service = (
        build_service_with_constraint_service()
    )
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.PROPOSE_CONSTRAINT,
        source_message_ids=["review-message-1"],
        constraint_scope_type=ConstraintScopeType.ROLE,
        constraint_scope_id="role-1",
        constraint_type=ConstraintType.HARD_RULE,
        rule_text="Do not describe this role as enterprise-level.",
    )

    applied_action = service.apply_action(action.id)
    constraint = constraint_service.constraints[applied_action.applied_constraint_id]

    assert applied_action.status == FactReviewActionStatus.APPLIED
    assert applied_action.applied_constraint_id == constraint.id
    assert applied_action.applied_fact_id is None
    assert review_repository.get_action(action.id) == applied_action
    assert constraint.scope_type == ConstraintScopeType.ROLE
    assert constraint.scope_id == "role-1"
    assert constraint.constraint_type == ConstraintType.HARD_RULE
    assert constraint.rule_text == "Do not describe this role as enterprise-level."
    assert constraint.source_message_ids == ["review-message-1"]


def test_fact_review_service_rejects_apply_for_non_proposed_action() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )
    service.reject_action(action.id)

    with pytest.raises(InvalidFactReviewActionStatusTransitionError, match="rejected"):
        service.apply_action(action.id)


def test_fact_review_service_rejects_missing_action() -> None:
    service, _review_repository, _fact_service = build_service()

    with pytest.raises(FactReviewActionNotFoundError, match="action-1"):
        service.apply_action("action-1")


def test_fact_review_service_rejects_and_archives_actions() -> None:
    service, review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )

    rejected_action = service.reject_action(action.id)
    archived_action = service.archive_action(action.id)

    assert rejected_action.status == FactReviewActionStatus.REJECTED
    assert archived_action.status == FactReviewActionStatus.ARCHIVED
    assert review_repository.get_action(action.id) == archived_action


def test_fact_review_service_rejects_invalid_action_status_transition() -> None:
    service, _review_repository, fact_service = build_service()
    fact_service.save(build_fact())
    thread = service.start_thread("fact-1")
    action = service.add_action(
        thread_id=thread.id,
        action_type=FactReviewActionType.ACTIVATE_FACT,
    )
    archived_action = service.archive_action(action.id)

    with pytest.raises(InvalidFactReviewActionStatusTransitionError, match="archived"):
        service.reject_action(archived_action.id)
