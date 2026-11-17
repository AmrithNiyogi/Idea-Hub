"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Idea Hub spine API.

    Responsibilities:
    - Centralize env-driven knobs for DB, Redis, JWT, OTP, SMTP, and CORS.
    - Provide safe local-dev defaults (override in production).

    Side Effects:
    - Reads `.env` from the process working directory when present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: Literal["dev", "staging", "prod"] = "dev"
    APP_NAME: str = "IdeaKonnekt"
    API_PREFIX: str = "/api/v1"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    # Comma-separated extra browser origins (ngrok HTTPS UI, etc.).
    # FRONTEND_ORIGIN + localhost:5173 variants are always included.
    CORS_ORIGINS: str = ""
    # Public API origin embedded in agent handoff prompts / skill install copy
    # (no trailing slash). Agents also honor IDEA_HUB_API_URL in their env.
    PUBLIC_API_URL: str = "http://127.0.0.1:8000"

    DATABASE_URL: str = (
        "postgresql+asyncpg://ideahub:ideahub@127.0.0.1:15432/ideahub"
    )

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 16379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    JWT_SECRET_KEY: str = "IdeaHubDevSecretChangeMe!2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    LOGIN_OTP_TTL_SECONDS: int = 600
    LOGIN_OTP_MAX_ATTEMPTS: int = 5
    LOGIN_OTP_RESEND_COOLDOWN_SECONDS: int = 60
    # After OTP succeeds for multi-role users, ticket must be redeemed with a role.
    LOGIN_TICKET_TTL_SECONDS: int = 300

    # SMTP for login OTP delivery (STARTTLS on port 588 for emailsbit).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 588
    SMTP_SECURITY: Literal["STARTTLS", "SSL", "NONE"] = "STARTTLS"
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    # When set, OTP emails are delivered here instead of the login account email.
    OTP_EMAIL_OVERRIDE: str | None = None

    # Domain-event notification emails (decisions, collab, hours, …).
    # When NOTIFY_EMAIL_OVERRIDE is empty, OTP_EMAIL_OVERRIDE is used as To.
    NOTIFY_EMAIL_ENABLED: bool = True
    NOTIFY_EMAIL_OVERRIDE: str | None = None

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    SEED_PASSWORD: str = Field(
        default="IdeaHub!2026",
        description="Shared password for demo seed users.",
    )

    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Directory for user uploads (avatars); served at /uploads.",
    )

    # Microsoft Entra ID (Azure AD) OIDC — work/school accounts (M365 / Teams users).
    # Leave empty / MICROSOFT_ENABLED=false until Azure app registration is filled in.
    MICROSOFT_ENABLED: bool = False
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = Field(
        default="common",
        description=(
            "Entra authority tenant: 'common' (orgs + MSA), 'organizations' "
            "(work/school only), 'consumers' (MSA only), or a directory GUID "
            "(single-tenant). Must align with Azure Supported account types."
        ),
    )
    MICROSOFT_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/microsoft/callback"
    )
    MICROSOFT_FRONTEND_SUCCESS_URL: str = Field(
        default="http://localhost:5173/",
        description=(
            "Default frontend landing after Microsoft SSO when no relative "
            "redirect path was requested. Origin is also used as the base for "
            "non-default redirect paths."
        ),
    )
    MICROSOFT_DEFAULT_ROLE: str = Field(
        default="contributor",
        description="Primary role assigned to users created via Microsoft SSO.",
    )
    MICROSOFT_SSO_STATE_TTL_SECONDS: int = 600

    # Agent seam: when True (default), submit-assist / help / review briefs use
    # local heuristics only. Set False once AI Studio execute env is filled in
    # (see docs/AGENT_SIMULATION.md). Live path: POST /api/v2/runs/execute.
    SIMULATE_AGENTS: bool = True

    # AI Studio / Kompass API Gateway (runs/execute). Placeholders only in
    # .env.example — put real project-slug / tool tokens in local .env.
    AISTUDIO_API_BASE_URL: str = Field(
        default="",
        description=(
            "API Gateway origin with no trailing slash, e.g. "
            "https://aistudio-apigateway-v2-staging.dotkonnekt.com"
        ),
    )
    AISTUDIO_TENANT_ID: str = Field(
        default="",
        description="X-Tenant-ID header value (staging often 'devtest').",
    )
    AISTUDIO_PROJECT_SLUG: str = Field(
        default="",
        description="project-slug header; required for public/project-scoped execute.",
    )
    AISTUDIO_TOOL_AUTH_TOKEN: str = Field(
        default="",
        description=(
            "Optional X-Authorization value forwarded for tool auth. "
            "Leave empty when agents do not call authenticated tools."
        ),
    )
    AISTUDIO_EXECUTE_TIMEOUT_SECONDS: int = Field(
        default=120,
        description="HTTP timeout for POST /api/v2/runs/execute (and poll budget).",
    )
    # Kompass agent id or slug per Idea Hub surface (fill after agents exist).
    AISTUDIO_AGENT_SUBMIT_ASSIST: str = ""
    AISTUDIO_AGENT_HELP: str = ""
    AISTUDIO_AGENT_IDEA_OPTIMIZER: str = ""
    AISTUDIO_AGENT_REVIEW_INTELLIGENCE: str = ""

    # Optional OAuth app credentials for future ClickUp / Jira OAuth flows.
    # MVP uses per-user API tokens / webhook secrets stored encrypted in DB.
    # Leave blank until an OAuth app is registered; never commit real secrets.
    CLICKUP_CLIENT_ID: str = ""
    CLICKUP_CLIENT_SECRET: str = ""
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    # Optional default webhook for local demos of custom_webhook provider.
    TRACKER_CUSTOM_WEBHOOK_URL: str = ""
    TRACKER_CUSTOM_AUTH_HEADER: str = ""

    def allowed_cors_origins(self) -> list[str]:
        """Build the CORS allowlist for credentialed browser calls.

        Always includes ``FRONTEND_ORIGIN`` and local Vite origins, then any
        extra entries from ``CORS_ORIGINS`` (comma-separated). Trailing slashes
        are stripped. Order is preserved; duplicates are dropped.

        Returns:
            list[str]: Absolute origins suitable for ``CORSMiddleware.allow_origins``.
        """
        origins: list[str] = []
        seen: set[str] = set()
        candidates = [
            self.FRONTEND_ORIGIN,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            *self.CORS_ORIGINS.split(","),
        ]
        for raw in candidates:
            origin = raw.strip().rstrip("/")
            if not origin or origin in seen:
                continue
            seen.add(origin)
            origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()


settings = get_settings()
