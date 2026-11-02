"""Spaced-repetition engine: 1 → 3 → 7 → 15 → 30 → 60 days."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RevisionItem

INTERVALS = [1, 3, 7, 15, 30, 60]


def schedule(db: Session, user_id: int, question_id: int) -> None:
    exists = db.scalar(
        select(RevisionItem).where(RevisionItem.user_id == user_id, RevisionItem.question_id == question_id)
    )
    if exists is None:
        db.add(
            RevisionItem(
                user_id=user_id,
                question_id=question_id,
                stage=0,
                lapses=0,
                completed=False,
                due_on=date.today() + timedelta(days=INTERVALS[0]),
            )
        )


def review(item: RevisionItem, recalled: bool) -> None:
    today = date.today()
    item.last_reviewed_at = datetime.now(timezone.utc)
    if recalled:
        item.stage += 1
        if item.stage >= len(INTERVALS):
            item.stage = len(INTERVALS)
            item.completed = True
        else:
            item.due_on = today + timedelta(days=INTERVALS[item.stage])
    else:
        item.lapses += 1
        item.stage = 0
        item.due_on = today + timedelta(days=INTERVALS[0])
