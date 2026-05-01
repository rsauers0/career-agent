from __future__ import annotations

from career_agent.errors import (
    EvidenceReferenceRemovalError,
    FactNotFoundError,
    FactRoleMismatchError,
    RoleNotFoundError,
    SourceNotFoundError,
    SourceRoleMismatchError,
)
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_facts.repository import ExperienceFactRepository
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.repository import RoleSourceRepository


class ExperienceFactService:
    """Application behavior for canonical experience facts."""

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
        return fact

    def save_fact(self, fact: ExperienceFact) -> None:
        """Persist an existing fact after validating its references."""

        self._validate_role_and_sources(role_id=fact.role_id, source_ids=fact.source_ids)
        self._validate_fact_link(role_id=fact.role_id, fact_id=fact.supersedes_fact_id)
        self._validate_fact_link(role_id=fact.role_id, fact_id=fact.superseded_by_fact_id)
        self._validate_append_only_evidence_references(fact)
        self.fact_repository.save(fact)

    def delete_fact(self, fact_id: str) -> bool:
        """Delete one saved fact by identifier."""

        return self.fact_repository.delete(fact_id)

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
                    "Experience fact evidence references cannot be removed: "
                    f"{field_name}={removed}"
                )
                raise EvidenceReferenceRemovalError(msg)
