from __future__ import annotations

from career_agent.errors import RoleNotFoundError, SourceNotFoundError, SourceRoleMismatchError
from career_agent.experience_bullets.models import ExperienceBullet
from career_agent.experience_bullets.repository import ExperienceBulletRepository
from career_agent.experience_roles.repository import ExperienceRoleRepository
from career_agent.role_sources.repository import RoleSourceRepository


class ExperienceBulletService:
    """Application behavior for canonical experience bullets."""

    def __init__(
        self,
        bullet_repository: ExperienceBulletRepository,
        role_repository: ExperienceRoleRepository,
        source_repository: RoleSourceRepository,
    ) -> None:
        self.bullet_repository = bullet_repository
        self.role_repository = role_repository
        self.source_repository = source_repository

    def list_bullets(self, role_id: str | None = None) -> list[ExperienceBullet]:
        """Return saved bullets, optionally filtered by role id."""

        return self.bullet_repository.list(role_id=role_id)

    def get_bullet(self, bullet_id: str) -> ExperienceBullet | None:
        """Return one saved bullet if it exists."""

        return self.bullet_repository.get(bullet_id)

    def add_bullet(
        self,
        role_id: str,
        text: str,
        source_ids: list[str] | None = None,
    ) -> ExperienceBullet:
        """Create a canonical bullet for an existing role."""

        self._validate_role_and_sources(role_id=role_id, source_ids=source_ids or [])
        bullet = ExperienceBullet(
            role_id=role_id,
            source_ids=source_ids or [],
            text=text,
        )
        self.bullet_repository.save(bullet)
        return bullet

    def save_bullet(self, bullet: ExperienceBullet) -> None:
        """Persist an existing bullet after validating its references."""

        self._validate_role_and_sources(role_id=bullet.role_id, source_ids=bullet.source_ids)
        self.bullet_repository.save(bullet)

    def delete_bullet(self, bullet_id: str) -> bool:
        """Delete one saved bullet by identifier."""

        return self.bullet_repository.delete(bullet_id)

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
