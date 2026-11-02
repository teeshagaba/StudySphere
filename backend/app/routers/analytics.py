from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Question, RevisionItem, StudySession, User, UserBadge, UserQuestion, XPEvent
from ..services.gamification import BADGES, active_days, as_date, level_for, streaks, xp_for_level
from ..services.mastery import topic_mastery
from .career import funnel

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = date.today()

    by_difficulty = dict(
        db.execute(
            select(Question.difficulty, func.count())
            .select_from(UserQuestion)
            .join(Question, Question.id == UserQuestion.question_id)
            .where(UserQuestion.user_id == user.id, UserQuestion.status == "solved")
            .group_by(Question.difficulty)
        ).all()
    )
    total_questions = dict(db.execute(select(Question.difficulty, func.count()).group_by(Question.difficulty)).all())

    year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    heatmap = [
        {"date": as_date(d).isoformat(), "count": c}
        for d, c in db.execute(
            select(func.date(XPEvent.created_at), func.count())
            .where(XPEvent.user_id == user.id, XPEvent.created_at >= year_ago)
            .group_by(func.date(XPEvent.created_at))
        ).all()
    ]

    week_ago = datetime.now(timezone.utc) - timedelta(days=6)
    week_minutes = {
        as_date(d): m
        for d, m in db.execute(
            select(func.date(StudySession.started_at), func.sum(StudySession.duration_min))
            .where(StudySession.user_id == user.id, StudySession.started_at >= week_ago)
            .group_by(func.date(StudySession.started_at))
        ).all()
    }
    total_minutes = db.scalar(
        select(func.coalesce(func.sum(StudySession.duration_min), 0)).where(StudySession.user_id == user.id)
    )

    mastery = [m for m in topic_mastery(db, user.id) if m["total"]]
    current, longest = streaks(active_days(db, user.id))
    owned = dict(db.execute(select(UserBadge.code, UserBadge.earned_at).where(UserBadge.user_id == user.id)).all())
    level = level_for(user.xp)

    return {
        "user": {
            "name": user.name,
            "xp": user.xp,
            "level": level,
            "level_floor_xp": xp_for_level(level),
            "next_level_xp": xp_for_level(level + 1),
        },
        "solved": {"total": sum(by_difficulty.values()), **{d: by_difficulty.get(d, 0) for d in ("Easy", "Medium", "Hard")}},
        "total_questions": sum(total_questions.values()),
        "solved_today": db.scalar(
            select(func.count()).select_from(UserQuestion).where(
                UserQuestion.user_id == user.id,
                UserQuestion.status == "solved",
                func.date(UserQuestion.solved_at) == today.isoformat(),
            )
        ),
        "streak": {"current": current, "longest": longest},
        "heatmap": heatmap,
        "study_week": [
            {"date": (today - timedelta(days=i)).isoformat(), "minutes": int(week_minutes.get(today - timedelta(days=i), 0))}
            for i in range(6, -1, -1)
        ],
        "study_hours_total": round(total_minutes / 60, 1),
        "strong_topics": [m for m in mastery if m["mastery"] > 0][:5],
        "weak_topics": sorted(mastery, key=lambda m: m["mastery"])[:5],
        "revision_due": db.scalar(
            select(func.count()).select_from(RevisionItem).where(
                RevisionItem.user_id == user.id, RevisionItem.completed.is_(False), RevisionItem.due_on <= today
            )
        ),
        "career": funnel(user, db),
        "badges": [
            {"code": code, "name": name, "description": desc, "earned_at": owned[code].isoformat() if code in owned else None}
            for code, (name, desc) in BADGES.items()
        ],
    }
