"""
Authentication middleware.
- JWT in httpOnly cookie (ADR-005)
- Multi-tenant isolation (G2)
- Human verification support (G3)
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.settings import settings


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract user from httpOnly cookie. Returns full User object."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        # Fallback: check Authorization header for API clients
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            raise HTTPException(status_code=401, detail="No autenticado")

    payload = decode_token(token)
    user_id = uuid.UUID(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Cuenta inactiva")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """Dependency factory — restrict endpoint to specific roles."""
    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Rol {current_user.role} no tiene permisos para esta acción",
            )
        return current_user
    return _check


async def require_org_access(
    resource_id: uuid.UUID,
    table: str,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    G2 — Multi-tenant isolation.
    Verifies that resource belongs to the user's organization.
    master_admin bypasses this check.
    """
    if current_user.role == "master_admin":
        return

    result = await db.execute(
        text(f"SELECT id FROM {table} WHERE id = :id AND organization_id = :org_id"),
        {"id": resource_id, "org_id": current_user.organization_id},
    )
    if not result.first():
        raise HTTPException(status_code=403, detail="Acceso denegado")
