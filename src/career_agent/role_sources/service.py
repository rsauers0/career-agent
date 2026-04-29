from __future__ import annotations

from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.role_sources.repository import RoleSourceRepository


class RoleNotFoundError(Exception):
    """Raised when source material is added for a missing role."""


class RoleSourceService:
    """Application behavior for role source entries."""

    def __init__(
        self,
        source_repository: RoleSourceRepository,
        role_repository: ExperienceRoleRepository,
    ) -> None:
        self.source_repository = source_repository
        self.role_repository = role_repository

    def list_sources(self, role_id: str | None = None) -> list[RoleSourceEntry]:
        """Return saved source entries, optionally filtered by role id."""

        return self.source_repository.list(role_id=role_id)

    def get_source(self, source_id: str) -> RoleSourceEntry | None:
        """Return one saved source entry if it exists."""

        return self.source_repository.get(source_id)

    def add_source(self, role_id: str, source_text: str) -> RoleSourceEntry:
        """Create a source entry for an existing experience role."""

        if self.role_repository.get(role_id) is None:
            msg = f"Experience role does not exist: {role_id}"
            raise RoleNotFoundError(msg)

        source = RoleSourceEntry(role_id=role_id, source_text=source_text)
        self.source_repository.save(source)
        return source

    def delete_source(self, source_id: str) -> bool:
        """Delete one saved source entry by identifier."""

        return self.source_repository.delete(source_id)
