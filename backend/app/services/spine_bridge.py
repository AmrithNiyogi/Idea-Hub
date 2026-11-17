"""Soft reads/writes against spine idea/user tables.

Phase 2+3 must not own the ideas lifecycle. This bridge uses raw SQLAlchemy
text/table access when ORM models exist, and degrades gracefully with clear
errors when spine tables are missing.

Expected spine idea columns used here (when present):
  id, title, status, author_id, owner_id, co_author_ids (JSONB/array),
  anonymous, ideathon_id, updated_at

Expected user columns: id, name, email, roles, team_id, title
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class IdeaRef:
    id: uuid.UUID
    title: str
    status: str
    author_id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    co_author_ids: list[uuid.UUID] = field(default_factory=list)
    anonymous: bool = False
    ideathon_id: Optional[uuid.UUID] = None
    problem: str = ""
    solution: str = ""


@dataclass
class UserRef:
    id: uuid.UUID
    name: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)
    team_id: Optional[uuid.UUID] = None
    title: str = ""


class SpineBridge:
    """Read/update helpers for spine-owned rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_idea(self, idea_id: uuid.UUID) -> Optional[IdeaRef]:
        try:
            row = (
                await self.session.execute(
                    text(
                        """
                        SELECT id, title, status, author_id, owner_id,
                               COALESCE(co_author_ids, '[]'::jsonb) AS co_author_ids,
                               COALESCE(anonymous, false) AS anonymous,
                               ideathon_id,
                               COALESCE(problem, '') AS problem,
                               COALESCE(solution, '') AS solution
                        FROM ideas WHERE id = :id
                        """
                    ),
                    {"id": idea_id},
                )
            ).mappings().first()
        except Exception:  # noqa: BLE001 — table/columns may not exist yet
            # Fallback without optional columns
            try:
                row = (
                    await self.session.execute(
                        text(
                            """
                            SELECT id, title, status, author_id, owner_id
                            FROM ideas WHERE id = :id
                            """
                        ),
                        {"id": idea_id},
                    )
                ).mappings().first()
            except Exception:  # noqa: BLE001
                return None
            if not row:
                return None
            return IdeaRef(
                id=row["id"],
                title=row["title"],
                status=row["status"],
                author_id=row["author_id"],
                owner_id=row.get("owner_id"),
            )
        if not row:
            return None
        co = row.get("co_author_ids") or []
        if isinstance(co, str):
            import json

            co = json.loads(co)
        co_ids = [
            c if isinstance(c, uuid.UUID) else uuid.UUID(str(c)) for c in co
        ]
        return IdeaRef(
            id=row["id"],
            title=row["title"],
            status=row["status"],
            author_id=row["author_id"],
            owner_id=row.get("owner_id"),
            co_author_ids=co_ids,
            anonymous=bool(row.get("anonymous")),
            ideathon_id=row.get("ideathon_id"),
            problem=str(row.get("problem") or ""),
            solution=str(row.get("solution") or ""),
        )

    async def set_idea_status(
        self,
        idea_id: uuid.UUID,
        status: str,
        *,
        actor_id: uuid.UUID,
        reason: str = "",
    ) -> None:
        """Best-effort status update + history insert if spine tables exist."""
        now = datetime.now(timezone.utc)
        await self.session.execute(
            text(
                """
                UPDATE ideas
                SET status = :status, updated_at = :now
                WHERE id = :id
                """
            ),
            {"status": status, "now": now, "id": idea_id},
        )
        try:
            await self.session.execute(
                text(
                    """
                    INSERT INTO status_history
                      (id, idea_id, from_status, to_status, actor_id, at, reason)
                    SELECT gen_random_uuid(), :idea_id, status, :to_status,
                           :actor_id, :at, :reason
                    FROM ideas WHERE id = :idea_id
                    """
                ),
                {
                    "idea_id": idea_id,
                    "to_status": status,
                    "actor_id": actor_id,
                    "at": now,
                    "reason": reason,
                },
            )
        except Exception:  # noqa: BLE001 — history table shape may differ
            pass

    async def set_idea_ideathon(
        self, idea_id: uuid.UUID, ideathon_id: Optional[uuid.UUID]
    ) -> None:
        try:
            await self.session.execute(
                text(
                    "UPDATE ideas SET ideathon_id = :ith, updated_at = :now WHERE id = :id"
                ),
                {
                    "ith": ideathon_id,
                    "now": datetime.now(timezone.utc),
                    "id": idea_id,
                },
            )
        except Exception:  # noqa: BLE001 — column may not exist yet
            pass

    async def get_user(self, user_id: uuid.UUID) -> Optional[UserRef]:
        try:
            row = (
                await self.session.execute(
                    text(
                        """
                        SELECT id, name, email, roles, team_id, title
                        FROM users WHERE id = :id
                        """
                    ),
                    {"id": user_id},
                )
            ).mappings().first()
        except Exception:  # noqa: BLE001
            try:
                row = (
                    await self.session.execute(
                        text("SELECT id, name, email FROM users WHERE id = :id"),
                        {"id": user_id},
                    )
                ).mappings().first()
            except Exception:  # noqa: BLE001
                return None
            if not row:
                return None
            return UserRef(
                id=row["id"],
                name=row.get("name") or "",
                email=row.get("email") or "",
            )
        if not row:
            return None
        roles = row.get("roles") or []
        if isinstance(roles, str):
            import json

            roles = json.loads(roles)
        return UserRef(
            id=row["id"],
            name=row.get("name") or "",
            email=row.get("email") or "",
            roles=[str(r) for r in roles],
            team_id=row.get("team_id"),
            title=row.get("title") or "",
        )

    async def ideas_for_author(
        self, user_id: uuid.UUID
    ) -> Sequence[dict[str, Any]]:
        try:
            rows = (
                await self.session.execute(
                    text(
                        """
                        SELECT id, title, status, author_id, owner_id, co_author_ids
                        FROM ideas
                        WHERE author_id = :uid
                           OR owner_id = :uid
                           OR co_author_ids @> to_jsonb(ARRAY[:uid]::uuid[])
                        """
                    ),
                    {"uid": user_id},
                )
            ).mappings().all()
            return [dict(r) for r in rows]
        except Exception:  # noqa: BLE001
            try:
                rows = (
                    await self.session.execute(
                        text(
                            """
                            SELECT id, title, status, author_id, owner_id
                            FROM ideas
                            WHERE author_id = :uid OR owner_id = :uid
                            """
                        ),
                        {"uid": user_id},
                    )
                ).mappings().all()
                return [dict(r) for r in rows]
            except Exception:  # noqa: BLE001
                return []
