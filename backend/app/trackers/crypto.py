"""Fernet helpers for tracker credential blobs (same key derivation as TOTP).

Tradeoff (MVP):
- Credentials are encrypted at rest with a key derived from ``JWT_SECRET_KEY``.
- Rotation of JWT secret invalidates stored tracker tokens (reconnect required).
- Prefer a dedicated ``TRACKER_CREDENTIALS_KEY`` later for independent rotation.
- Never log decrypted credentials or write them to git.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.config.settings import settings

logger = logging.getLogger("idea_hub.trackers.crypto")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(plain: dict[str, Any]) -> str:
    """Serialize and encrypt a credentials dict for column storage."""
    raw = json.dumps(plain, separators=(",", ":"), sort_keys=True)
    return _fernet().encrypt(raw.encode("utf-8")).decode("utf-8")


def decrypt_credentials(token: str) -> dict[str, Any]:
    """Decrypt a stored credentials blob.

    Raises:
        HTTPException: 500 if ciphertext is corrupt or the key changed.
    """
    try:
        plain = _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        data = json.loads(plain)
        if not isinstance(data, dict):
            raise ValueError("credentials payload is not an object")
        return data
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        logger.error("Tracker credentials decrypt failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Stored tracker credentials are invalid. "
                "Disconnect and reconnect the provider."
            ),
        ) from exc
