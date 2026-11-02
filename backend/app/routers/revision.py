from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Question, RevisionItem, User, UserQuestion
from ..services import revision
from ..services.gamification import REVISION_XP, award_xp, check_badges

router = APIRouter(prefix="/revision", tags=["revision"])


def _serialize(item: RevisionItem) -> dict:
    q = item.question
    return {
        "id": item.id,
        "question": {"id": q.id, "title": q.title, "difficulty": q.difficulty, "url": q.url},
        "stage": item.stage,
        "interval_days": revision.INTERVALS[min(item.stage, len(revision.INTERVALS) - 1)],
        "due_on": item.due_on.isoformat(),
        "lapses": item.lapses,
        "completed": item.completed,
    }


@router.get("")
def overview(days: int = 14, user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = date.today()
    # Solved problems from before the engine existed (or imported) get scheduled too.
    missing = db.scalars(
        select(UserQuestion.question_id).where(
            UserQuestion.user_id == user.id,
            UserQuestion.status == "solved",
            UserQuestion.question_id.not_in(select(RevisionItem.question_id).where(RevisionItem.user_id == user.id)),
        )
    ).all()
    for qid in missing:
        revision.schedule(db, user.id, qid)
    if missing:
        db.commit()

    items = db.scalars(
        select(RevisionItem)
        .where(
            RevisionItem.user_id == user.id,
            RevisionItem.completed.is_(False),
            RevisionItem.due_on <= today + timedelta(days=min(days, 90)),
        )
        .order_by(RevisionItem.due_on)
    ).all()
    attempted = db.scalars(
        select(Question)
        .join(UserQuestion, UserQuestion.question_id == Question.id)
        .where(UserQuestion.user_id == user.id, UserQuestion.status == "attempted")
        .order_by(UserQuestion.updated_at.desc())
        .limit(20)
    ).all()
    return {
        "intervals": revision.INTERVALS,
        "due": [_serialize(i) for i in items if i.due_on <= today],
        "upcoming": [_serialize(i) for i in items if i.due_on > today],
        "attempted": [{"id": q.id, "title": q.title, "difficulty": q.difficulty, "url": q.url} for q in attempted],
        "total_tracked": db.scalar(
            select(func.count()).select_from(RevisionItem).where(RevisionItem.user_id == user.id)
        ),
    }


@router.post("/add/{question_id}", status_code=201)
def add(question_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Puts a problem in today's revision queue."""
    if db.get(Question, question_id) is None:
        raise HTTPException(404, "Question not found")
    item = db.scalar(
        select(RevisionItem).where(RevisionItem.user_id == user.id, RevisionItem.question_id == question_id)
    )
    if item is None:
        item = RevisionItem(user_id=user.id, question_id=question_id, stage=0, lapses=0, completed=False,
                            due_on=date.today())
        db.add(item)
    else:
        item.completed = False
        item.due_on = date.today()
    db.commit()
    return _serialize(item)


class ReviewIn(BaseModel):
    recalled: bool


@router.post("/{item_id}/review")
def review(item_id: int, body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(RevisionItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(404, "Revision item not found")
    revision.review(item, body.recalled)
    award_xp(db, user, "revision", REVISION_XP)
    new_badges = check_badges(db, user)
    db.commit()
    return {"item": _serialize(item), "xp_gained": REVISION_XP, "new_badges": new_badges}
