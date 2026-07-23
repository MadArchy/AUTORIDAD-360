"""Autenticación JWT + refresh HttpOnly."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models.org import AppUser, OrgMembership
from app.services.auth import (
    REFRESH_COOKIE_NAME,
    create_access_token,
    create_refresh_session,
    revoke_all_user_sessions,
    revoke_refresh_session,
    rotate_refresh_session,
    verify_password,
)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    roles_by_org: dict[str, str]
    expires_in_minutes: int


def _roles_for_user(db: Session, user: AppUser) -> dict[str, str]:
    roles_by_org: dict[str, str] = {}
    if user.is_superadmin:
        roles_by_org["all"] = "superadmin"
        return roles_by_org
    memberships = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.user_id == user.id,
            OrgMembership.is_active.is_(True),
        )
        .all()
    )
    for membership in memberships:
        if membership.organization:
            roles_by_org[membership.organization.slug] = membership.role
    return roles_by_org


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure or settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_days * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=LoginResponse)
def login_access_token(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = (
        db.query(AppUser)
        .filter(
            AppUser.email == credentials.email.lower().strip(),
            AppUser.is_active.is_(True),
        )
        .first()
    )
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciales inválidas")

    roles_by_org = _roles_for_user(db, user)
    access = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_raw, _ = create_refresh_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, refresh_raw)
    return LoginResponse(
        access_token=access,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        roles_by_org=roles_by_org,
        expires_in_minutes=settings.jwt_access_token_minutes,
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        new_raw, _, user_id = rotate_refresh_session(
            db,
            raw_token=raw,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = db.query(AppUser).filter(AppUser.id == user_id, AppUser.is_active.is_(True)).first()
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Usuario no disponible")

    _set_refresh_cookie(response, new_raw)
    return LoginResponse(
        access_token=create_access_token(
            data={"sub": str(user.id), "email": user.email}
        ),
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        roles_by_org=_roles_for_user(db, user),
        expires_in_minutes=settings.jwt_access_token_minutes,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    revoke_refresh_session(db, raw_token=request.cookies.get(REFRESH_COOKIE_NAME))
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/logout-all")
def logout_all_sessions(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    user_id = None
    if raw:
        from app.services.auth import _hash_token
        from app.models.auth_sessions import AuthSession

        row = (
            db.query(AuthSession)
            .filter(AuthSession.token_hash == _hash_token(raw))
            .first()
        )
        if row:
            user_id = row.user_id
    if user_id is not None:
        revoke_all_user_sessions(db, user_id=user_id)
    _clear_refresh_cookie(response)
    return {"ok": True, "user_id": user_id}
