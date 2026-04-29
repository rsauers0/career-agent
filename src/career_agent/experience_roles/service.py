from __future__ import annotations

from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_roles.repository import ExperienceRoleRepository


class ExperienceRoleService:
    """Application behavior for experience roles."""

    def __init__(self, repository: ExperienceRoleRepository) -> None:
        self.repository = repository

    def list_roles(self) -> list[ExperienceRole]:
        """Return saved experience roles in repository-defined order."""

        return self.repository.list()

    def get_role(self, role_id: str) -> ExperienceRole | None:
        """Return one saved experience role if it exists."""

        return self.repository.get(role_id)

    def save_role(self, role: ExperienceRole) -> None:
        """Validate and persist an experience role."""

        self.repository.save(role)

    def delete_role(self, role_id: str) -> bool:
        """Delete one experience role by identifier."""

        return self.repository.delete(role_id)
