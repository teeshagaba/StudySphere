from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Company, Question, QuestionCompany, Sheet, SheetQuestion, Tag, User, UserQuestion
from ..services import revision
from ..services.catalog import slugify, upsert_question
from ..services.gamification import SOLVE_XP, award_xp, check_badges

router = APIRouter(prefix="/dsa", tags=["dsa"])

Difficulty = Literal["Easy", "Medium", "Hard"]
Status = Literal["todo", "attempted", "solved"]


def _visible_sheets(user: User):
    return or_(Sheet.owner_id.is_(None), Sheet.owner_id == user.id)


def _progress(db: Session, user_id: int, question_ids: list[int]) -> dict[int, UserQuestion]:
    if not question_ids:
        return {}
    rows = db.scalars(
        select(UserQuestion).where(UserQuestion.user_id == user_id, UserQuestion.question_id.in_(question_ids))
    )
    return {uq.question_id: uq for uq in rows}


def _sheet_names(db: Session, user: User, question_ids: list[int]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = defaultdict(list)
    if not question_ids:
        return out
    for qid, name in db.execute(
        select(SheetQuestion.question_id, Sheet.name)
        .join(Sheet, Sheet.id == SheetQuestion.sheet_id)
        .where(SheetQuestion.question_id.in_(question_ids), _visible_sheets(user))
    ):
        out[qid].append(name)
    return out


def _serialize(q: Question, uq: UserQuestion | None, sheets: list[str], section: str | None = None) -> dict:
    return {
        "id": q.id,
        "slug": q.slug,
        "title": q.title,
        "difficulty": q.difficulty,
        "url": q.url,
        "platform": q.platform,
        "topics": [t.name for t in q.tags if t.kind == "topic"],
        "patterns": [t.name for t in q.tags if t.kind == "pattern"],
        "companies": sorted(
            ({"name": qc.company.name, "frequency": qc.frequency} for qc in q.companies),
            key=lambda c: -c["frequency"],
        ),
        "sheets": sheets,
        "section": section,
        "status": uq.status if uq else "todo",
        "confidence": uq.confidence if uq else None,
        "attempts": uq.attempts if uq else 0,
    }


@router.get("/questions")
def list_questions(
    topic: str | None = None,
    pattern: str | None = None,
    company: str | None = None,
    difficulty: Difficulty | None = None,
    sheet: str | None = None,
    status: Status | None = None,
    q: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if topic:
        stmt = stmt.where(Question.tags.any((Tag.name == topic) & (Tag.kind == "topic")))
    if pattern:
        stmt = stmt.where(Question.tags.any((Tag.name == pattern) & (Tag.kind == "pattern")))
    if company:
        stmt = stmt.where(Question.companies.any(QuestionCompany.company.has(Company.name == company)))
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if sheet:
        stmt = stmt.where(
            Question.id.in_(
                select(SheetQuestion.question_id)
                .join(Sheet, Sheet.id == SheetQuestion.sheet_id)
                .where(Sheet.slug == sheet, _visible_sheets(user))
            )
        )
    if q:
        stmt = stmt.where(Question.title.ilike(f"%{q[:100]}%"))

    questions = db.scalars(stmt.order_by(Question.id)).all()
    ids = [x.id for x in questions]
    progress = _progress(db, user.id, ids)
    sheets = _sheet_names(db, user, ids)
    items = [_serialize(x, progress.get(x.id), sheets.get(x.id, [])) for x in questions]
    if status:
        items = [i for i in items if i["status"] == status]
    return items


@router.get("/filters")
def filters(db: Session = Depends(get_db), _: User = Depends(current_user)):
    tags = db.scalars(select(Tag).order_by(Tag.name)).all()
    return {
        "topics": [t.name for t in tags if t.kind == "topic"],
        "patterns": [t.name for t in tags if t.kind == "pattern"],
        "companies": list(db.scalars(select(Company.name).order_by(Company.name))),
    }


@router.get("/sheets")
def list_sheets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Sheet, func.count(SheetQuestion.question_id), func.count(UserQuestion.id))
        .outerjoin(SheetQuestion, SheetQuestion.sheet_id == Sheet.id)
        .outerjoin(
            UserQuestion,
            (UserQuestion.question_id == SheetQuestion.question_id)
            & (UserQuestion.user_id == user.id)
            & (UserQuestion.status == "solved"),
        )
        .where(_visible_sheets(user))
        .group_by(Sheet.id)
        .order_by(Sheet.kind.desc(), Sheet.name)
    ).all()
    return [
        {"slug": s.slug, "name": s.name, "description": s.description, "kind": s.kind, "total": total, "solved": solved}
        for s, total, solved in rows
    ]


@router.get("/sheets/{slug}")
def get_sheet(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sheet = db.scalar(select(Sheet).where(Sheet.slug == slug, _visible_sheets(user)))
    if sheet is None:
        raise HTTPException(404, "Sheet not found")
    ids = [i.question_id for i in sheet.items]
    progress = _progress(db, user.id, ids)
    sheets = _sheet_names(db, user, ids)
    return {
        "slug": sheet.slug,
        "name": sheet.name,
        "description": sheet.description,
        "questions": [
            _serialize(i.question, progress.get(i.question_id), sheets.get(i.question_id, []), i.section)
            for i in sheet.items
        ],
    }


class ProgressIn(BaseModel):
    status: Status
    confidence: int | None = Field(None, ge=1, le=5)
    time_spent_min: int = Field(0, ge=0, le=600)


@router.post("/questions/{question_id}/progress")
def update_progress(
    question_id: int, body: ProgressIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(404, "Question not found")

    uq = db.scalar(
        select(UserQuestion).where(UserQuestion.user_id == user.id, UserQuestion.question_id == question_id)
    )
    if uq is None:
        uq = UserQuestion(user_id=user.id, question_id=question_id, status="todo", attempts=0, time_spent_min=0)
        db.add(uq)

    newly_solved = body.status == "solved" and uq.status != "solved"
    if body.status != uq.status and body.status in ("attempted", "solved"):
        uq.attempts += 1
    uq.status = body.status
    uq.time_spent_min += body.time_spent_min
    if body.confidence is not None:
        uq.confidence = body.confidence

    xp = 0
    if newly_solved:
        uq.solved_at = datetime.now(timezone.utc)
        xp = SOLVE_XP.get(question.difficulty, 10)
        award_xp(db, user, f"solve:{question.slug}", xp)
        revision.schedule(db, user.id, question_id)
    new_badges = check_badges(db, user)
    db.commit()

    synced = _sheet_names(db, user, [question_id]).get(question_id, [])
    return {
        "question": _serialize(question, uq, synced),
        "synced_sheets": synced,
        "xp_gained": xp,
        "new_badges": new_badges,
    }


class ImportQuestion(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    difficulty: Difficulty = "Medium"
    url: HttpUrl | None = None
    slug: str | None = Field(None, max_length=200)
    section: str | None = Field(None, max_length=80)
    topics: list[str] = Field(default_factory=list, max_length=20)
    patterns: list[str] = Field(default_factory=list, max_length=20)
    companies: dict[str, int] = Field(default_factory=dict)


class SheetImport(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=2000)
    questions: list[ImportQuestion] = Field(min_length=1, max_length=2000)


@router.post("/sheets/import")
def import_sheet(body: SheetImport, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Import any sheet; entries are matched to canonical questions so existing progress carries over."""
    slug = f"u{user.id}-{slugify(body.name)}"
    if db.scalar(select(Sheet).where(Sheet.slug == slug)):
        raise HTTPException(409, "You already have a sheet with this name")
    sheet = Sheet(slug=slug, name=body.name, description=body.description, kind="custom", owner_id=user.id)
    db.add(sheet)
    seen: set[int] = set()
    for pos, item in enumerate(body.questions):
        q = upsert_question(
            db,
            title=item.title.strip(),
            difficulty=item.difficulty,
            url=str(item.url) if item.url else None,
            slug=item.slug,
            topics=[t.strip()[:80] for t in item.topics if t.strip()],
            patterns=[p.strip()[:80] for p in item.patterns if p.strip()],
            companies={c.strip()[:120]: max(1, min(f, 10)) for c, f in item.companies.items() if c.strip()},
        )
        if q.id not in seen:
            seen.add(q.id)
            sheet.items.append(SheetQuestion(question=q, position=pos, section=item.section))
    db.commit()
    already = db.scalar(
        select(func.count()).select_from(UserQuestion).where(
            UserQuestion.user_id == user.id, UserQuestion.status == "solved", UserQuestion.question_id.in_(seen)
        )
    )
    return {"slug": slug, "imported": len(seen), "already_solved": already}
