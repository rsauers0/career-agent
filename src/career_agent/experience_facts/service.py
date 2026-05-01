from __future__ import annotations

from career_agent.errors import RoleNotFoundError, SourceNotFoundError, SourceRoleMismatchError
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
    ) -> ExperienceFact:
        """Create a canonical fact for an existing role."""

        self._validate_role_and_sources(role_id=role_id, source_ids=source_ids or [])
        fact = ExperienceFact(
            role_id=role_id,
            source_ids=source_ids or [],
            text=text,
        )
        self.fact_repository.save(fact)
        return fact

    def save_fact(self, fact: ExperienceFact) -> None:
        """Persist an existing fact after validating its references."""

        self._validate_role_and_sources(role_id=fact.role_id, source_ids=fact.source_ids)
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
