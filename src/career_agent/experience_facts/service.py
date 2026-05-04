from __future__ import annotations

from datetime import UTC, datetime

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
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.repository import RoleSourceRepository


class ExperienceFactService:
    """Application behavior for canonical experience facts."""

    _ALLOWED_TRANSITIONS: dict[ExperienceFactStatus, set[ExperienceFactStatus]] = {
        ExperienceFactStatus.DRAFT: {
            ExperienceFactStatus.ACTIVE,
            ExperienceFactStatus.NEEDS_CLARIFICATION,
            ExperienceFactStatus.REJECTED,
        },
        ExperienceFactStatus.NEEDS_CLARIFICATION: {
            ExperienceFactStatus.DRAFT,
            ExperienceFactStatus.REJECTED,
        },
        ExperienceFactStatus.ACTIVE: {
            ExperienceFactStatus.SUPERSEDED,
            ExperienceFactStatus.ARCHIVED,
        },
        ExperienceFactStatus.REJECTED: {
            ExperienceFactStatus.ARCHIVED,
        },
        ExperienceFactStatus.SUPERSEDED: {
            ExperienceFactStatus.ARCHIVED,
        },
        ExperienceFactStatus.ARCHIVED: set(),
    }

    def __init__(
        self,
        fact_repository: ExperienceFactRepository,
        role_repository: ExperienceRoleRepository,
        source_repository: RoleSourceRepository,
    ) -> None:
        self.fact_repository = fact_repository
        self.role_repository = role_repository
        self.source_repository = source_repository

    def list_facts(self, role_id: str | None = None) -> list[ExperienceFact]:
        """Return saved facts, optionally filtered by role id."""

        return self.fact_repository.list(role_id=role_id)

    def get_fact(self, fact_id: str) -> ExperienceFact | None:
        """Return one saved fact if it exists."""

        return self.fact_repository.get(fact_id)

    def add_fact(
        self,
        role_id: str,
        text: str,
        source_ids: list[str] | None = None,
        question_ids: list[str] | None = None,
        message_ids: list[str] | None = None,
        details: list[str] | None = None,
        systems: list[str] | None = None,
        skills: list[str] | None = None,
        functions: list[str] | None = None,
        supersedes_fact_id: str | None = None,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Create a canonical fact for an existing role."""

        self._validate_role_and_sources(role_id=role_id, source_ids=source_ids or [])
        self._validate_fact_link(role_id=role_id, fact_id=supersedes_fact_id)
        fact = ExperienceFact(
            role_id=role_id,
            source_ids=source_ids or [],
            question_ids=question_ids or [],
            message_ids=message_ids or [],
            text=text,
            details=details or [],
            systems=systems or [],
            skills=skills or [],
            functions=functions or [],
            supersedes_fact_id=supersedes_fact_id,
        )
        self.fact_repository.save(fact)
        self._record_change_event(
            fact=fact,
            event_type=FactChangeEventType.CREATED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
            to_status=fact.status,
            related_fact_id=supersedes_fact_id,
        )
        return fact

    def save_fact(self, fact: ExperienceFact) -> None:
        """Persist an existing fact after validating its references."""

        self._validate_role_and_sources(role_id=fact.role_id, source_ids=fact.source_ids)
        self._validate_fact_link(role_id=fact.role_id, fact_id=fact.supersedes_fact_id)
        self._validate_fact_link(role_id=fact.role_id, fact_id=fact.superseded_by_fact_id)
        self._validate_append_only_evidence_references(fact)
        self._validate_saved_fact_lifecycle_rules(fact)
        self.fact_repository.save(fact)

    def activate_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Activate a draft fact and supersede its prior fact when applicable."""

        fact = self._get_required_fact(fact_id)
        self._validate_status_transition(fact.status, ExperienceFactStatus.ACTIVE)
        superseded_fact = None
        if fact.supersedes_fact_id is not None:
            superseded_fact = self._get_required_fact(fact.supersedes_fact_id)
            self._validate_status_transition(
                superseded_fact.status,
                ExperienceFactStatus.SUPERSEDED,
            )

        activated_fact = self._with_status(fact, ExperienceFactStatus.ACTIVE)
        self.save_fact(activated_fact)
        self._record_change_event(
            fact=activated_fact,
            event_type=FactChangeEventType.ACTIVATED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
            from_status=fact.status,
            to_status=activated_fact.status,
            related_fact_id=activated_fact.supersedes_fact_id,
        )

        if superseded_fact is not None:
            from_status = superseded_fact.status
            superseded_fact = superseded_fact.model_copy(
                update={
                    "status": ExperienceFactStatus.SUPERSEDED,
                    "superseded_by_fact_id": activated_fact.id,
                    "updated_at": self._now(),
                }
            )
            self.save_fact(superseded_fact)
            self._record_change_event(
                fact=superseded_fact,
                event_type=FactChangeEventType.SUPERSEDED,
                actor=actor,
                summary=summary,
                source_message_ids=source_message_ids or [],
                from_status=from_status,
                to_status=superseded_fact.status,
                related_fact_id=activated_fact.id,
            )

        return activated_fact

    def mark_needs_clarification(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Mark a draft fact as needing additional clarification."""

        return self._transition_fact(
            fact_id=fact_id,
            new_status=ExperienceFactStatus.NEEDS_CLARIFICATION,
            event_type=FactChangeEventType.NEEDS_CLARIFICATION,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
        )

    def return_to_draft(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Return a needs-clarification fact to draft status."""

        return self._transition_fact(
            fact_id=fact_id,
            new_status=ExperienceFactStatus.DRAFT,
            event_type=FactChangeEventType.RETURNED_TO_DRAFT,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
        )

    def reject_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Reject a draft or needs-clarification fact."""

        return self._transition_fact(
            fact_id=fact_id,
            new_status=ExperienceFactStatus.REJECTED,
            event_type=FactChangeEventType.REJECTED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
        )

    def archive_fact(
        self,
        fact_id: str,
        actor: FactChangeActor = FactChangeActor.USER,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
    ) -> ExperienceFact:
        """Archive a fact when its current lifecycle status allows it."""

        return self._transition_fact(
            fact_id=fact_id,
            new_status=ExperienceFactStatus.ARCHIVED,
            event_type=FactChangeEventType.ARCHIVED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
        )

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
        """Revise a fact according to lifecycle rules."""

        fact = self._get_required_fact(fact_id)
        source_ids = source_ids or []
        source_message_ids = source_message_ids or []
        self._validate_role_and_sources(role_id=fact.role_id, source_ids=source_ids)

        if fact.status in {ExperienceFactStatus.DRAFT, ExperienceFactStatus.NEEDS_CLARIFICATION}:
            revised_fact = self._build_revised_fact(
                fact=fact,
                text=text,
                source_ids=source_ids,
                question_ids=question_ids or [],
                message_ids=message_ids or [],
                details=details or [],
                systems=systems or [],
                skills=skills or [],
                functions=functions or [],
                status=fact.status,
                supersedes_fact_id=fact.supersedes_fact_id,
                superseded_by_fact_id=fact.superseded_by_fact_id,
            )
            self.save_fact(revised_fact)
            self._record_revision_events(
                original_fact=fact,
                revised_fact=revised_fact,
                actor=actor,
                summary=summary,
                source_message_ids=source_message_ids,
            )
            return revised_fact

        if fact.status == ExperienceFactStatus.ACTIVE:
            revised_fact = self._build_revised_fact(
                fact=fact,
                text=text,
                source_ids=source_ids,
                question_ids=question_ids or [],
                message_ids=message_ids or [],
                details=details or [],
                systems=systems or [],
                skills=skills or [],
                functions=functions or [],
                status=ExperienceFactStatus.DRAFT,
                supersedes_fact_id=fact.id,
                superseded_by_fact_id=None,
                new_id=True,
            )
            self.save_fact(revised_fact)
            self._record_change_event(
                fact=revised_fact,
                event_type=FactChangeEventType.REVISED,
                actor=actor,
                summary=summary,
                source_message_ids=source_message_ids,
                to_status=revised_fact.status,
                related_fact_id=fact.id,
            )
            if self._has_added_evidence(fact, revised_fact):
                self._record_change_event(
                    fact=revised_fact,
                    event_type=FactChangeEventType.EVIDENCE_ADDED,
                    actor=actor,
                    summary=summary,
                    source_message_ids=source_message_ids,
                    to_status=revised_fact.status,
                    related_fact_id=fact.id,
                )
            return revised_fact

        msg = f"Experience fact cannot be revised while status is {fact.status.value}."
        raise FactRevisionNotAllowedError(msg)

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
        """Append evidence references to a fact through an explicit workflow."""

        fact = self._get_required_fact(fact_id)
        if fact.status in {
            ExperienceFactStatus.REJECTED,
            ExperienceFactStatus.SUPERSEDED,
            ExperienceFactStatus.ARCHIVED,
        }:
            msg = f"Experience fact cannot have evidence added while status is {fact.status.value}."
            raise FactRevisionNotAllowedError(msg)

        source_ids = source_ids or []
        question_ids = question_ids or []
        message_ids = message_ids or []
        source_message_ids = source_message_ids or []
        self._validate_role_and_sources(role_id=fact.role_id, source_ids=source_ids)
        updated_fact = fact.model_copy(
            update={
                "source_ids": self._merge_values(fact.source_ids, source_ids),
                "question_ids": self._merge_values(fact.question_ids, question_ids),
                "message_ids": self._merge_values(fact.message_ids, message_ids),
                "updated_at": self._now(),
            }
        )

        if not self._has_added_evidence(fact, updated_fact):
            return fact

        self.fact_repository.save(updated_fact)
        self._record_change_event(
            fact=updated_fact,
            event_type=FactChangeEventType.EVIDENCE_ADDED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids,
            from_status=fact.status,
            to_status=updated_fact.status,
        )
        return updated_fact

    def delete_fact(self, fact_id: str) -> bool:
        """Delete one saved fact by identifier."""

        return self.fact_repository.delete(fact_id)

    def list_change_events(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactChangeEvent]:
        """Return fact change events, optionally filtered by fact or role."""

        return self.fact_repository.list_change_events(fact_id=fact_id, role_id=role_id)

    def _get_required_fact(self, fact_id: str) -> ExperienceFact:
        """Return a fact or raise a domain error."""

        fact = self.fact_repository.get(fact_id)
        if fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)
        return fact

    def _transition_fact(
        self,
        fact_id: str,
        new_status: ExperienceFactStatus,
        event_type: FactChangeEventType,
        actor: FactChangeActor,
        summary: str | None,
        source_message_ids: list[str],
    ) -> ExperienceFact:
        """Apply a strict lifecycle transition to one fact."""

        fact = self._get_required_fact(fact_id)
        self._validate_status_transition(fact.status, new_status)
        updated_fact = self._with_status(fact, new_status)
        self.save_fact(updated_fact)
        self._record_change_event(
            fact=updated_fact,
            event_type=event_type,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids,
            from_status=fact.status,
            to_status=new_status,
        )
        return updated_fact

    def _with_status(
        self,
        fact: ExperienceFact,
        status: ExperienceFactStatus,
    ) -> ExperienceFact:
        """Return a copy of a fact with a new status and update timestamp."""

        return fact.model_copy(update={"status": status, "updated_at": self._now()})

    def _record_revision_events(
        self,
        original_fact: ExperienceFact,
        revised_fact: ExperienceFact,
        actor: FactChangeActor,
        summary: str | None,
        source_message_ids: list[str],
    ) -> None:
        """Record revision and evidence-added events for an in-place revision."""

        self._record_change_event(
            fact=revised_fact,
            event_type=FactChangeEventType.REVISED,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids,
            from_status=original_fact.status,
            to_status=revised_fact.status,
        )
        if self._has_added_evidence(original_fact, revised_fact):
            self._record_change_event(
                fact=revised_fact,
                event_type=FactChangeEventType.EVIDENCE_ADDED,
                actor=actor,
                summary=summary,
                source_message_ids=source_message_ids,
                from_status=original_fact.status,
                to_status=revised_fact.status,
            )

    def _record_change_event(
        self,
        fact: ExperienceFact,
        event_type: FactChangeEventType,
        actor: FactChangeActor,
        summary: str | None = None,
        source_message_ids: list[str] | None = None,
        from_status: ExperienceFactStatus | None = None,
        to_status: ExperienceFactStatus | None = None,
        related_fact_id: str | None = None,
    ) -> None:
        """Persist a semantic fact change event."""

        event = FactChangeEvent(
            fact_id=fact.id,
            role_id=fact.role_id,
            event_type=event_type,
            actor=actor,
            summary=summary,
            source_message_ids=source_message_ids or [],
            from_status=from_status,
            to_status=to_status,
            related_fact_id=related_fact_id,
        )
        self.fact_repository.save_change_event(event)

    def _has_added_evidence(
        self,
        existing_fact: ExperienceFact,
        updated_fact: ExperienceFact,
    ) -> bool:
        """Return whether an update adds evidence references."""

        for field_name in ("source_ids", "question_ids", "message_ids"):
            existing_values = set(getattr(existing_fact, field_name))
            updated_values = set(getattr(updated_fact, field_name))
            if updated_values - existing_values:
                return True
        return False

    def _validate_status_transition(
        self,
        current_status: ExperienceFactStatus,
        new_status: ExperienceFactStatus,
    ) -> None:
        """Validate an experience fact lifecycle transition."""

        allowed_statuses = self._ALLOWED_TRANSITIONS[current_status]
        if new_status not in allowed_statuses:
            msg = (
                "Experience fact status transition is not allowed: "
                f"{current_status.value} -> {new_status.value}"
            )
            raise InvalidFactStatusTransitionError(msg)

    def _build_revised_fact(
        self,
        fact: ExperienceFact,
        text: str,
        source_ids: list[str],
        question_ids: list[str],
        message_ids: list[str],
        details: list[str],
        systems: list[str],
        skills: list[str],
        functions: list[str],
        status: ExperienceFactStatus,
        supersedes_fact_id: str | None,
        superseded_by_fact_id: str | None,
        new_id: bool = False,
    ) -> ExperienceFact:
        """Build an in-place or replacement fact revision."""

        created_at = self._now() if new_id else fact.created_at
        updated_at = self._now()
        if new_id:
            return ExperienceFact(
                role_id=fact.role_id,
                source_ids=self._merge_values(fact.source_ids, source_ids),
                question_ids=self._merge_values(fact.question_ids, question_ids),
                message_ids=self._merge_values(fact.message_ids, message_ids),
                text=text,
                details=details or fact.details,
                systems=systems or fact.systems,
                skills=skills or fact.skills,
                functions=functions or fact.functions,
                supersedes_fact_id=supersedes_fact_id,
                superseded_by_fact_id=superseded_by_fact_id,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
            )
        return ExperienceFact(
            id=fact.id,
            role_id=fact.role_id,
            source_ids=self._merge_values(fact.source_ids, source_ids),
            question_ids=self._merge_values(fact.question_ids, question_ids),
            message_ids=self._merge_values(fact.message_ids, message_ids),
            text=text,
            details=details or fact.details,
            systems=systems or fact.systems,
            skills=skills or fact.skills,
            functions=functions or fact.functions,
            supersedes_fact_id=supersedes_fact_id,
            superseded_by_fact_id=superseded_by_fact_id,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _merge_values(self, existing_values: list[str], new_values: list[str]) -> list[str]:
        """Append new values while preserving order and removing duplicates."""

        merged_values: list[str] = []
        for value in [*existing_values, *new_values]:
            if value not in merged_values:
                merged_values.append(value)
        return merged_values

    def _now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(UTC)

    def _validate_role_and_sources(self, role_id: str, source_ids: list[str]) -> None:
        """Validate that role and source references are internally consistent."""

        if self.role_repository.get(role_id) is None:
            msg = f"Experience role does not exist: {role_id}"
            raise RoleNotFoundError(msg)

        for source_id in source_ids:
            source = self.source_repository.get(source_id)
            if source is None:
                msg = f"Role source does not exist: {source_id}"
                raise SourceNotFoundError(msg)
            if source.role_id != role_id:
                msg = f"Role source {source_id} does not belong to role: {role_id}"
                raise SourceRoleMismatchError(msg)

    def _validate_fact_link(self, role_id: str, fact_id: str | None) -> None:
        """Validate an optional linked fact reference."""

        if fact_id is None:
            return

        linked_fact = self.fact_repository.get(fact_id)
        if linked_fact is None:
            msg = f"Experience fact does not exist: {fact_id}"
            raise FactNotFoundError(msg)
        if linked_fact.role_id != role_id:
            msg = f"Experience fact {fact_id} does not belong to role: {role_id}"
            raise FactRoleMismatchError(msg)

    def _validate_append_only_evidence_references(self, fact: ExperienceFact) -> None:
        """Ensure saved fact updates do not remove prior evidence ids."""

        existing_fact = self.fact_repository.get(fact.id)
        if existing_fact is None:
            return

        for field_name in ("source_ids", "question_ids", "message_ids"):
            existing_values = getattr(existing_fact, field_name)
            updated_values = set(getattr(fact, field_name))
            removed_values = [value for value in existing_values if value not in updated_values]
            if removed_values:
                removed = ", ".join(removed_values)
                msg = (
                    f"Experience fact evidence references cannot be removed: {field_name}={removed}"
                )
                raise EvidenceReferenceRemovalError(msg)

    def _validate_saved_fact_lifecycle_rules(self, fact: ExperienceFact) -> None:
        """Ensure direct saves cannot bypass lifecycle and revision rules."""

        existing_fact = self.fact_repository.get(fact.id)
        if existing_fact is None:
            return

        if existing_fact.status != fact.status:
            self._validate_status_transition(existing_fact.status, fact.status)

        if not self._has_content_change(existing_fact, fact):
            return

        if existing_fact.status in {
            ExperienceFactStatus.DRAFT,
            ExperienceFactStatus.NEEDS_CLARIFICATION,
        }:
            return

        msg = f"Experience fact cannot be revised while status is {existing_fact.status.value}."
        raise FactRevisionNotAllowedError(msg)

    def _has_content_change(
        self,
        existing_fact: ExperienceFact,
        updated_fact: ExperienceFact,
    ) -> bool:
        """Return whether a save changes fact content or evidence."""

        fields = (
            "source_ids",
            "question_ids",
            "message_ids",
            "text",
            "details",
            "systems",
            "skills",
            "functions",
        )
        return any(
            getattr(existing_fact, field_name) != getattr(updated_fact, field_name)
            for field_name in fields
        )
