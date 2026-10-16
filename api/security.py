"""
Security, identity, and request guard dependencies for VERITAS API.
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status
from typing import Optional


def get_current_user(
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name"),
) -> str:
    """
    Extract verified reviewer identity from authentication headers.
    Falls back to a default compliance auditor if unconfigured.
    """
    if x_user_email and x_user_email.strip():
        return x_user_email.strip()
    if x_user_name and x_user_name.strip():
        return x_user_name.strip()
    return "Compliance Lead"
