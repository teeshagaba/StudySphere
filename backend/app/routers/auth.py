import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, current_user, hash_password, verify_password
from ..db import get_db
from ..models import User
from ..services.gamification import level_for
from ..services.ratelimit import enforce

router = APIRouter(prefix="/auth", tags=["auth"])

HANDLE_PATTERN = r"^[A-Za-z0-9_.\-]{1,64}$"


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password too long")
        return v


class ProfileIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    codeforces_handle: str | None = Field(None, pattern=HANDLE_PATTERN)
    leetcode_handle: str | None = Field(None, pattern=HANDLE_PATTERN)


def _token(user: User) -> dict:
    return {"access_token": create_token(user.id), "token_type": "bearer"}


def _profile(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "xp": user.xp,
        "level": level_for(user.xp),
        "codeforces_handle": user.codeforces_handle,
        "leetcode_handle": user.leetcode_handle,
    }


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=body.name, password_hash=hash_password(body.password), xp=0)
    db.add(user)
    db.commit()
    return _token(user)


@router.post("/guest")
async def guest(request: Request, db: Session = Depends(get_db)):
    await enforce(request.client.host if request.client else "unknown", "guest", 30, 60 * 60)
    user = User(
        email=f"guest-{secrets.token_hex(8)}@guest.studysphere",
        name="Guest",
        # Random unusable password: guest accounts are token-only.
        password_hash=await run_in_threadpool(hash_password, secrets.token_urlsafe(32)),
        xp=0,
    )
    db.add(user)
    db.commit()
    return _token(user)


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    await enforce(form.username.lower(), "login", 10, 15 * 60)
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not await run_in_threadpool(verify_password, form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return _token(user)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _profile(user)


@router.patch("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    return _profile(user)
