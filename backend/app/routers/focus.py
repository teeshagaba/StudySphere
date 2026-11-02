from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import StudySession, User
from ..services.gamification import FOCUS_XP_PER_25_MIN, award_xp, check_badges

router = APIRouter(prefix="/focus", tags=["focus"])


class SessionIn(BaseModel):
    kind: Literal["pomodoro", "study"] = "pomodoro"
    topic: str | None = Field(None, max_length=120)
    duration_min: int = Field(ge=1, le=600)


@router.post("/sessions", status_code=201)
def log_session(body: SessionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = StudySession(user_id=user.id, **body.model_dump())
    db.add(session)
    xp = body.duration_min // 25 * FOCUS_XP_PER_25_MIN
    if xp:
        award_xp(db, user, "focus", xp)
    new_badges = check_badges(db, user)
    db.commit()
    return {"id": session.id, "xp_gained": xp, "new_badges": new_badges}


@router.get("/sessions")
def recent_sessions(days: int = 7, user: User = Depends(current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=min(max(days, 1), 365))
    sessions = db.scalars(
        select(StudySession)
        .where(StudySession.user_id == user.id, StudySession.started_at >= since)
        .order_by(StudySession.started_at.desc())
    ).all()
    return {
        "total_minutes": sum(s.duration_min for s in sessions),
        "sessions": [
            {"id": s.id, "kind": s.kind, "topic": s.topic, "duration_min": s.duration_min,
             "started_at": s.started_at.isoformat()}
            for s in sessions
        ],
    }
