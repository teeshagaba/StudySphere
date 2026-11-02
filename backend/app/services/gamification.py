import math
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Question, StudySession, User, UserBadge, UserQuestion, XPEvent

SOLVE_XP = {"Easy": 10, "Medium": 20, "Hard": 40}
REVISION_XP = 5
FOCUS_XP_PER_25_MIN = 10
LEARNING_XP = 15

BADGES: dict[str, tuple[str, str]] = {
    "first_blood": ("First Blood", "Solve your first problem"),
    "half_century": ("Half Century", "Solve 50 problems"),
    "centurion": ("Centurion", "Solve 100 problems"),
    "hard_hitter": ("Hard Hitter", "Solve 10 Hard problems"),
    "streak_7": ("On Fire", "Maintain a 7-day streak"),
    "streak_30": ("Unstoppable", "Maintain a 30-day streak"),
    "reviser": ("Memory Palace", "Complete 25 revisions"),
    "deep_work": ("Deep Work", "Log 10 hours of focus time"),
}


def level_for(xp: int) -> int:
    return int(math.sqrt(xp / 100)) + 1


def xp_for_level(level: int) -> int:
    return 100 * (level - 1) ** 2


def award_xp(db: Session, user: User, kind: str, xp: int) -> None:
    db.add(XPEvent(user_id=user.id, kind=kind, xp=xp))
    user.xp += xp


def as_date(value: date | str) -> date:
    # SQLite's date() returns a string; PostgreSQL returns a date.
    return date.fromisoformat(value) if isinstance(value, str) else value


def active_days(db: Session, user_id: int) -> list[date]:
    rows = db.scalars(select(func.date(XPEvent.created_at)).where(XPEvent.user_id == user_id).distinct())
    return sorted(as_date(d) for d in rows)


def streaks(days: list[date]) -> tuple[int, int]:
    if not days:
        return 0, 0
    longest = run = 1
    for a, b in zip(days, days[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        longest = max(longest, run)
    current = run if days[-1] >= date.today() - timedelta(days=1) else 0
    return current, longest


def check_badges(db: Session, user: User) -> list[str]:
    db.flush()
    owned = set(db.scalars(select(UserBadge.code).where(UserBadge.user_id == user.id)))
    solved_q = select(func.count()).select_from(UserQuestion).where(
        UserQuestion.user_id == user.id, UserQuestion.status == "solved"
    )
    solved = db.scalar(solved_q) or 0
    hard = db.scalar(
        solved_q.join(Question, Question.id == UserQuestion.question_id).where(Question.difficulty == "Hard")
    ) or 0
    revisions = db.scalar(
        select(func.count()).select_from(XPEvent).where(XPEvent.user_id == user.id, XPEvent.kind == "revision")
    ) or 0
    focus_min = db.scalar(
        select(func.coalesce(func.sum(StudySession.duration_min), 0)).where(StudySession.user_id == user.id)
    ) or 0
    _, longest = streaks(active_days(db, user.id))

    earned = {
        "first_blood": solved >= 1,
        "half_century": solved >= 50,
        "centurion": solved >= 100,
        "hard_hitter": hard >= 10,
        "streak_7": longest >= 7,
        "streak_30": longest >= 30,
        "reviser": revisions >= 25,
        "deep_work": focus_min >= 600,
    }
    new = [code for code, ok in earned.items() if ok and code not in owned]
    for code in new:
        db.add(UserBadge(user_id=user.id, code=code))
    return new
