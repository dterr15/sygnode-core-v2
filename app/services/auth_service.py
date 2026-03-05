"""Auth service — login, register, password hashing."""

import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.auth import create_access_token
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def login(db: AsyncSession, data: LoginRequest) -> tuple[User, Organization, str]:
    """Authenticate user. Returns (user, organization, jwt_token)."""
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if user.status != "active":
        raise HTTPException(status_code=403, detail="Cuenta inactiva")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org_result.scalar_one()

    token = create_access_token(user.id, user.organization_id, user.role)
    return user, org, token


async def register(db: AsyncSession, data: RegisterRequest) -> tuple[User, Organization, str]:
    """Register new organization + admin user."""
    # Check RUT uniqueness
    existing = await db.execute(
        select(Organization).where(Organization.rut == data.rut_organizacion)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="RUT ya registrado")

    # Create organization
    org = Organization(
        rut=data.rut_organizacion,
        name=data.nombre_organizacion,
        city=data.city,
    )
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        organization_id=org.id,
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role="admin_org",
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, org.id, user.role)
    return user, org, token
