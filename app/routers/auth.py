from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.audit import log_audit
from app.middleware.auth import CurrentUser
from app.models.organization import Organization
from app.schemas.auth import LoginRequest, RegisterRequest, LoginResponse, UserBrief, OrgBrief
from app.services.auth_service import login, register
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login_endpoint(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """T2: Login → Set-Cookie httpOnly + return user/org (never password_hash)."""
    user, org, token = await login(db, data)

    # Set httpOnly cookie (ADR-005)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expiration_hours * 3600,
    )

    await log_audit(db, org.id, user.id, "user.login")
    await db.commit()

    return LoginResponse(
        user=UserBrief(id=str(user.id), email=user.email, name=user.name, role=user.role),
        organization=OrgBrief(
            id=str(org.id), rut=org.rut, name=org.name,
            subscription_status=org.subscription_status,
        ),
    )


@router.get("/me")
async def me_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return current authenticated user and their organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one()
    return LoginResponse(
        user=UserBrief(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            role=current_user.role,
        ),
        organization=OrgBrief(
            id=str(org.id),
            rut=org.rut,
            name=org.name,
            subscription_status=org.subscription_status,
        ),
    )


@router.post("/logout")
async def logout_endpoint(response: Response):
    response.delete_cookie(settings.cookie_name)
    return {"success": True}


@router.post("/register", status_code=201)
async def register_endpoint(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user, org, token = await register(db, data)

    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expiration_hours * 3600,
    )

    await log_audit(db, org.id, user.id, "user.register")
    await db.commit()

    return LoginResponse(
        user=UserBrief(id=str(user.id), email=user.email, name=user.name, role=user.role),
        organization=OrgBrief(
            id=str(org.id), rut=org.rut, name=org.name,
            subscription_status=org.subscription_status,
        ),
    )
