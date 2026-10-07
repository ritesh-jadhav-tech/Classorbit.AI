from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.init_db import ensure_default_roles
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.auth import (
    BootstrapAdminRequest,
    BootstrapAdminResponse,
    RegisterRequest,
    RegisterResponse,
    Token,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthError, authenticate_user, create_user, token_for_user
from app.api.deps import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    try:
        user = create_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role_name=payload.role,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return RegisterResponse(user=UserRead.model_validate(user), token=Token(access_token=token_for_user(user)))


@router.post("/bootstrap-admin", response_model=BootstrapAdminResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdminRequest, db: Session = Depends(get_db)) -> BootstrapAdminResponse:
    ensure_default_roles(db)
    existing_admin = (
        db.execute(select(User).join(User.role).where(User.role.has(name=RoleName.ADMIN))).scalars().first()
    )
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An admin user already exists.")
    try:
        user = create_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role_name=RoleName.ADMIN,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    token = Token(access_token=token_for_user(user))
    return BootstrapAdminResponse(user_id=user.id, email=user.email, role=user.role_name, token=token)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    try:
        user = authenticate_user(db, form.username, form.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return Token(access_token=token_for_user(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
