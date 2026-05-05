from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from career_agent.errors import (
    ActiveFactReviewThreadExistsError,
    FactNotFoundError,
    FactReviewActionNotFoundError,
    FactReviewActionsAlreadyExistError,
    FactReviewThreadNotFoundError,
    FactRoleMismatchError,
    InvalidFactReviewActionStatusTransitionError,
    InvalidFactReviewThreadStatusTransitionError,
    InvalidLLMOutputError,
    RoleNotFoundError,
)
from career_agent.experience_facts.models import ExperienceFact, FactChangeActor
from career_agent.experience_roles.models import ExperienceRole
from career_agent.fact_review.action_generator import (
    DeterministicFactReviewActionGenerator,
    FactReviewActionGenerator,
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
from career_agent.fact_review.repository import FactReviewRepository
from career_agent.scoped_constraints.models import (
    ConstraintScopeType,
    ConstraintType,
    ScopedConstraint,
)
from career_agent.workflow_approval import (
    DummyWorkflowApprovalService,
    WorkflowApprovalRequest,
    WorkflowApprovalRequestType,
    WorkflowApprovalService,
    WorkflowApprovalStatus,
)

ALLOWED_FACT_REVIEW_THREAD_STATUS_TRANSITIONS: dict[
    FactReviewThreadStatus,
    set[FactReviewThreadStatus],
] = {
    FactReviewThreadStatus.OPEN: {
        FactReviewThreadStatus.RESOLVED,
        FactReviewThreadStatus.ARCHIVED,
    },
    FactReviewThreadStatus.RESOLVED: {FactReviewThreadStatus.ARCHIVED},
    FactReviewThreadStatus.ARCHIVED: set(),
}


ALLOWED_FACT_REVIEW_ACTION_STATUS_TRANSITIONS: dict[
    FactReviewActionStatus,
    set[FactReviewActionStatus],
] = {
    FactReviewActionStatus.PROPOSED: {
        FactReviewActionStatus.APPLIED,
        FactReviewActionStatus.REJECTED,
        FactReviewActionStatus.ARCHIVED,
    },
    FactReviewActionStatus.APPLIED: {FactReviewActionStatus.ARCHIVED},
    FactReviewActionStatus.REJECTED: {FactReviewActionStatus.ARCHIVED},
    FactReviewActionStatus.ARCHIVED: set(),
}


class ExperienceFactMutationService(Protocol):
    """Subset of ExperienceFactService used by fact review actions."""

    def get_fact(self, fact_id: str) -> ExperienceFact | None:
        """Return one saved fact if it exists."""
        ...

    def activate_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Activate a fact."""
        ...

    def reject_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Reject a fact."""
        ...

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
        """Revise a fact."""
        ...

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
        """Append evidence references to a fact."""
        ...


class ExperienceRoleLookupService(Protocol):
    """Subset of ExperienceRoleService used by fact review action generation."""

    def get_role(self, role_id: str) -> ExperienceRole | None:
        """Return one saved role if it exists."""
        ...


class ScopedConstraintWorkflowService(Protocol):
    """Subset of ScopedConstraintService used by fact review actions."""

    def list_applicable_constraints(
        self,
        role_id: str | None = None,
        fact_id: str | None = None,
    ) -> list[ScopedConstraint]:
        """Return active constraints applicable to a role or fact context."""
        ...

    def add_constraint(
        self,
        scope_type: ConstraintScopeType,
        constraint_type: ConstraintType,
        rule_text: str,
        scope_id: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ScopedConstraint:
        """Add a proposed scoped constraint."""
        ...


class FactReviewService:
    """Application behavior for fact review workflow artifacts."""

    def __init__(
        self,
        review_repository: FactReviewRepository,
        role_service: ExperienceRoleLookupService,
        fact_service: ExperienceFactMutationService,
        constraint_service: ScopedConstraintWorkflowService,
        action_generator: FactReviewActionGenerator | None = None,
        approval_service: WorkflowApprovalService | None = None,
    ) -> None:
        self.review_repository = review_repository
        self.role_service = role_service
        self.fact_service = fact_service
        self.constraint_service = constraint_service
        self.action_generator = action_generator or DeterministicFactReviewActionGenerator()
        self.approval_service = approval_service or DummyWorkflowApprovalService()

    @property
    def action_generator_name(self) -> str:
        """Return the display name for the configured action generator."""

        return self.action_generator.generator_name

    def list_threads(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewThread]:
        """Return fact review threads, optionally filtered by fact or role."""

        return self.review_repository.list_threads(fact_id=fact_id, role_id=role_id)

    def get_thread(self, thread_id: str) -> FactReviewThread | None:
        """Return one fact review thread if it exists."""

        return self.review_repository.get_thread(thread_id)

    def list_messages(self, thread_id: str) -> list[FactReviewMessage]:
        """Return messages for one fact review thread."""

        return self.review_repository.list_messages(thread_id)

    def list_actions(
        self,
        thread_id: str | None = None,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewAction]:
        """Return structured fact review actions."""

        return self.review_repository.list_actions(
            thread_id=thread_id,
            fact_id=fact_id,
            role_id=role_id,
        )

    def get_action(self, action_id: str) -> FactReviewAction | None:
        """Return one structured fact review action if it exists."""

        return self.review_repository.get_action(action_id)

    def start_thread(self, fact_id: str) -> FactReviewThread:
        """Start a fact review thread for an existing fact."""

        fact = self.fact_service.get_fact(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)

        self.ensure_no_open_thread_for_fact(fact_id)
        thread = FactReviewThread(fact_id=fact.id, role_id=fact.role_id)
        self.review_repository.save_thread(thread)
        return thread

    def add_message(
        self,
        thread_id: str,
        author: FactReviewMessageAuthor,
        message_text: str,
        recommended_action: FactReviewRecommendedAction = FactReviewRecommendedAction.NONE,
    ) -> FactReviewMessage:
        """Append one message to an existing fact review thread."""

        self._get_required_thread(thread_id)
        message = FactReviewMessage(
            thread_id=thread_id,
            author=author,
            message_text=message_text,
            recommended_action=recommended_action,
        )
        self.review_repository.save_message(message)
        return message

    def add_action(
        self,
        thread_id: str,
        action_type: FactReviewActionType,
        rationale: str | None = None,
        source_message_ids: list[str] | None = None,
        revised_text: str | None = None,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        constraint_scope_type: ConstraintScopeType | None = None,
        constraint_scope_id: str | None = None,
        constraint_type: ConstraintType | None = None,
        rule_text: str | None = None,
    ) -> FactReviewAction:
        """Add a structured action proposal to a fact review thread."""

        thread = self._get_required_thread(thread_id)
        action = FactReviewAction(
            thread_id=thread.id,
            fact_id=thread.fact_id,
            role_id=thread.role_id,
            action_type=action_type,
            rationale=rationale,
            source_message_ids=source_message_ids or [],
            revised_text=revised_text,
            source_ids=source_ids or [],
            question_ids=question_ids or [],
            message_ids=message_ids or [],
            constraint_scope_type=constraint_scope_type,
            constraint_scope_id=constraint_scope_id,
            constraint_type=constraint_type,
            rule_text=rule_text,
        )
        self.review_repository.save_action(action)
        return action

    def generate_actions(self, thread_id: str) -> list[FactReviewAction]:
        """Generate structured action proposals for one open fact review thread."""

        thread = self._get_required_thread(thread_id)
        if thread.status != FactReviewThreadStatus.OPEN:
            msg = (
                f"Cannot generate fact review actions for thread {thread.id} "
                f"while status is {thread.status.value}."
            )
            raise InvalidFactReviewThreadStatusTransitionError(msg)

        existing_actions = self.review_repository.list_actions(thread_id=thread.id)
        proposed_actions = [
            action
            for action in existing_actions
            if action.status == FactReviewActionStatus.PROPOSED
        ]
        if proposed_actions:
            action_ids = ", ".join(action.id for action in proposed_actions)
            msg = f"Proposed fact review actions already exist for thread {thread.id}: {action_ids}"
            raise FactReviewActionsAlreadyExistError(msg)

        fact = self.fact_service.get_fact(thread.fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {thread.fact_id}"
            raise FactNotFoundError(msg)
        if fact.role_id != thread.role_id:
            msg = f"Experience fact {fact.id} does not belong to role: {thread.role_id}"
            raise FactRoleMismatchError(msg)

        role = self.role_service.get_role(thread.role_id)
        if role is None:
            msg = f"Experience role does not exist: {thread.role_id}"
            raise RoleNotFoundError(msg)

        messages = self.review_repository.list_messages(thread.id)
        constraints = self.constraint_service.list_applicable_constraints(
            role_id=thread.role_id,
            fact_id=thread.fact_id,
        )
        generated_actions = self.action_generator.generate_actions(
            role=role,
            fact=fact,
            thread=thread,
            messages=messages,
            existing_actions=existing_actions,
            constraints=constraints,
        )
        self._validate_generated_actions(
            generated_actions=generated_actions,
            messages=messages,
        )

        saved_actions: list[FactReviewAction] = []
        for generated_action in generated_actions:
            saved_actions.append(
                self.add_action(
                    thread_id=thread.id,
                    action_type=generated_action.action_type,
                    rationale=generated_action.rationale,
                    source_message_ids=generated_action.source_message_ids,
                    revised_text=generated_action.revised_text,
                    source_ids=generated_action.source_ids,
                    question_ids=generated_action.question_ids,
                    message_ids=generated_action.message_ids,
                    constraint_scope_type=generated_action.constraint_scope_type,
                    constraint_scope_id=generated_action.constraint_scope_id,
                    constraint_type=generated_action.constraint_type,
                    rule_text=generated_action.rule_text,
                )
            )
        return saved_actions

    def apply_action(
        self,
        action_id: str,
        actor: FactChangeActor = FactChangeActor.SYSTEM,
    ) -> FactReviewAction:
        """Apply one proposed review action through deterministic services."""

        action = self._get_required_action(action_id)
        if action.status != FactReviewActionStatus.PROPOSED:
            self._raise_invalid_action_transition(action, FactReviewActionStatus.APPLIED)

        if action.action_type == FactReviewActionType.PROPOSE_CONSTRAINT:
            applied_constraint = self._apply_constraint_action(action)
            applied_action = self._build_action_update(
                action,
                status=FactReviewActionStatus.APPLIED,
                applied_constraint_id=applied_constraint.id,
            )
            self.review_repository.save_action(applied_action)
            return applied_action

        if action.action_type == FactReviewActionType.ACTIVATE_FACT:
            approval_result = self.approval_service.request_approval(
                WorkflowApprovalRequest(
                    request_type=WorkflowApprovalRequestType.FACT_ACTIVATION,
                    subject_id=action.fact_id,
                    role_id=action.role_id,
                    rationale=action.rationale,
                    source_message_ids=action.source_message_ids,
                )
            )
            if approval_result.status == WorkflowApprovalStatus.REJECTED:
                rejected_action = self._build_action_update(
                    action,
                    status=FactReviewActionStatus.REJECTED,
                    rationale=self._approval_rejection_rationale(
                        action=action,
                        approval_rationale=approval_result.rationale,
                    ),
                )
                self.review_repository.save_action(rejected_action)
                return rejected_action

        applied_fact = self._apply_fact_action(action=action, actor=actor)
        applied_action = self._build_action_update(
            action,
            status=FactReviewActionStatus.APPLIED,
            applied_fact_id=applied_fact.id,
        )
        self.review_repository.save_action(applied_action)
        return applied_action

    def reject_action(self, action_id: str) -> FactReviewAction:
        """Reject one proposed fact review action."""

        return self._set_action_status(
            action_id=action_id,
            status=FactReviewActionStatus.REJECTED,
        )

    def archive_action(self, action_id: str) -> FactReviewAction:
        """Archive a fact review action."""

        return self._set_action_status(
            action_id=action_id,
            status=FactReviewActionStatus.ARCHIVED,
        )

    def resolve_thread(self, thread_id: str) -> FactReviewThread:
        """Mark an open fact review thread as resolved."""

        return self._set_thread_status(
            thread_id=thread_id,
            status=FactReviewThreadStatus.RESOLVED,
        )

    def archive_thread(self, thread_id: str) -> FactReviewThread:
        """Archive a fact review thread."""

        return self._set_thread_status(
            thread_id=thread_id,
            status=FactReviewThreadStatus.ARCHIVED,
        )

    def ensure_no_open_thread_for_fact(self, fact_id: str) -> None:
        """Validate that a fact does not already have an open review thread."""

        for thread in self.review_repository.list_threads(fact_id=fact_id):
            if thread.status == FactReviewThreadStatus.OPEN:
                msg = f"Open fact review thread already exists for fact {fact_id}: {thread.id}"
                raise ActiveFactReviewThreadExistsError(msg)

    def _get_required_thread(self, thread_id: str) -> FactReviewThread:
        """Return one fact review thread or raise a domain error."""

        thread = self.review_repository.get_thread(thread_id)
        if thread is None:
            msg = f"Fact review thread does not exist: {thread_id}"
            raise FactReviewThreadNotFoundError(msg)
        return thread

    def _get_required_action(self, action_id: str) -> FactReviewAction:
        """Return one fact review action or raise a domain error."""

        action = self.review_repository.get_action(action_id)
        if action is None:
            msg = f"Fact review action does not exist: {action_id}"
            raise FactReviewActionNotFoundError(msg)
        return action

    def _set_thread_status(
        self,
        thread_id: str,
        status: FactReviewThreadStatus,
    ) -> FactReviewThread:
        """Persist an explicit fact review thread status transition."""

        thread = self._get_required_thread(thread_id)
        allowed_statuses = ALLOWED_FACT_REVIEW_THREAD_STATUS_TRANSITIONS[thread.status]
        if status not in allowed_statuses:
            msg = (
                f"Cannot transition fact review thread {thread.id} "
                f"from {thread.status.value} to {status.value}."
            )
            raise InvalidFactReviewThreadStatusTransitionError(msg)

        updated_thread = thread.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.review_repository.save_thread(updated_thread)
        return updated_thread

    def _set_action_status(
        self,
        action_id: str,
        status: FactReviewActionStatus,
    ) -> FactReviewAction:
        """Persist an explicit fact review action status transition."""

        action = self._get_required_action(action_id)
        allowed_statuses = ALLOWED_FACT_REVIEW_ACTION_STATUS_TRANSITIONS[action.status]
        if status not in allowed_statuses:
            self._raise_invalid_action_transition(action, status)

        updated_action = self._build_action_update(action, status=status)
        self.review_repository.save_action(updated_action)
        return updated_action

    def _apply_fact_action(
        self,
        action: FactReviewAction,
        actor: FactChangeActor,
    ) -> ExperienceFact:
        """Dispatch one proposed action to the canonical fact service."""

        summary = action.rationale or f"Applied fact review action {action.id}."
        if action.action_type == FactReviewActionType.ACTIVATE_FACT:
            return self.fact_service.activate_fact(
                fact_id=action.fact_id,
                actor=actor,
                summary=summary,
                source_message_ids=action.source_message_ids,
            )

        if action.action_type == FactReviewActionType.REJECT_FACT:
            return self.fact_service.reject_fact(
                fact_id=action.fact_id,
                actor=actor,
                summary=summary,
                source_message_ids=action.source_message_ids,
            )

        if action.action_type == FactReviewActionType.REVISE_FACT:
            return self.fact_service.revise_fact(
                fact_id=action.fact_id,
                text=action.revised_text or "",
                source_ids=action.source_ids,
                question_ids=action.question_ids,
                message_ids=action.message_ids,
                actor=actor,
                summary=summary,
                source_message_ids=action.source_message_ids,
            )

        if action.action_type == FactReviewActionType.ADD_EVIDENCE:
            return self.fact_service.add_evidence(
                fact_id=action.fact_id,
                source_ids=action.source_ids,
                question_ids=action.question_ids,
                message_ids=action.message_ids,
                actor=actor,
                summary=summary,
                source_message_ids=action.source_message_ids,
            )

        msg = f"Fact review action is not a fact action: {action.action_type.value}"
        raise ValueError(msg)

    def _apply_constraint_action(self, action: FactReviewAction) -> ScopedConstraint:
        """Create a proposed scoped constraint from a review action."""

        if (
            action.constraint_scope_type is None
            or action.constraint_type is None
            or action.rule_text is None
        ):
            msg = f"Fact review action is missing constraint fields: {action.id}"
            raise ValueError(msg)

        return self.constraint_service.add_constraint(
            scope_type=action.constraint_scope_type,
            scope_id=action.constraint_scope_id,
            constraint_type=action.constraint_type,
            rule_text=action.rule_text,
            source_message_ids=action.source_message_ids,
        )

    def _build_action_update(
        self,
        action: FactReviewAction,
        status: FactReviewActionStatus,
        applied_fact_id: str | None = None,
        applied_constraint_id: str | None = None,
        rationale: str | None = None,
    ) -> FactReviewAction:
        """Build a validated copy of a fact review action with updated status."""

        action_data = action.model_dump()
        action_data.update(
            {
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        if applied_fact_id is not None:
            action_data["applied_fact_id"] = applied_fact_id
        if applied_constraint_id is not None:
            action_data["applied_constraint_id"] = applied_constraint_id
        if rationale is not None:
            action_data["rationale"] = rationale
        return FactReviewAction.model_validate(action_data)

    def _approval_rejection_rationale(
        self,
        action: FactReviewAction,
        approval_rationale: str | None,
    ) -> str:
        """Return rationale text that preserves the proposal and approval result."""

        rejection_text = approval_rationale or "Approval workflow rejected activation."
        if action.rationale is None:
            return f"Approval rejected: {rejection_text}"
        return f"{action.rationale}\n\nApproval rejected: {rejection_text}"

    def _raise_invalid_action_transition(
        self,
        action: FactReviewAction,
        status: FactReviewActionStatus,
    ) -> None:
        """Raise a consistent action lifecycle transition error."""

        msg = (
            f"Cannot transition fact review action {action.id} "
            f"from {action.status.value} to {status.value}."
        )
        raise InvalidFactReviewActionStatusTransitionError(msg)

    def _validate_generated_actions(
        self,
        generated_actions: list[GeneratedFactReviewAction],
        messages: list[FactReviewMessage],
    ) -> None:
        """Validate generated action proposals against the review thread context."""

        message_ids = {message.id for message in messages}
        seen_keys: set[
            tuple[
                str,
                str | None,
                tuple[str, ...],
                tuple[str, ...],
                tuple[str, ...],
                str | None,
                str | None,
                str | None,
                str | None,
            ]
        ] = set()
        for generated_action in generated_actions:
            for message_id in generated_action.source_message_ids:
                if message_id not in message_ids:
                    msg = f"Generated action referenced unknown review message id: {message_id}"
                    raise InvalidLLMOutputError(msg)

            key = self._generated_action_key(generated_action)
            if key in seen_keys:
                msg = "Generated action proposals contain duplicates."
                raise InvalidLLMOutputError(msg)
            seen_keys.add(key)

    def _generated_action_key(
        self,
        generated_action: GeneratedFactReviewAction,
    ) -> tuple[
        str,
        str | None,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        """Return a semantic duplicate key for a generated action proposal."""

        return (
            generated_action.action_type.value,
            generated_action.revised_text,
            tuple(generated_action.source_ids),
            tuple(generated_action.question_ids),
            tuple(generated_action.message_ids),
            generated_action.constraint_scope_type.value
            if generated_action.constraint_scope_type
            else None,
            generated_action.constraint_scope_id,
            generated_action.constraint_type.value if generated_action.constraint_type else None,
            generated_action.rule_text,
        )
