from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Note, Question, User, UserQuestion
from ..services import ai
from ..services.ratelimit import enforce

router = APIRouter(prefix="/notes", tags=["notes"])

NoteKind = Literal["question", "topic", "ai", "personal", "interview"]


class NoteIn(BaseModel):
    kind: NoteKind
    title: str = Field(min_length=1, max_length=200)
    content: str = Field("", max_length=100_000)
    question_id: int | None = None
    topic: str | None = Field(None, max_length=80)


def _serialize(n: Note) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "title": n.title,
        "content": n.content,
        "question_id": n.question_id,
        "topic": n.topic,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


def _owned(db: Session, user: User, note_id: int) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(404, "Note not found")
    return note


@router.get("")
def list_notes(
    kind: NoteKind | None = None,
    q: str | None = None,
    question_id: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Note).where(Note.user_id == user.id)
    if kind:
        stmt = stmt.where(Note.kind == kind)
    if question_id:
        stmt = stmt.where(Note.question_id == question_id)
    if q:
        pattern = f"%{q[:100]}%"
        stmt = stmt.where(or_(Note.title.ilike(pattern), Note.content.ilike(pattern), Note.topic.ilike(pattern)))
    return [_serialize(n) for n in db.scalars(stmt.order_by(Note.updated_at.desc()).limit(500))]


@router.post("", status_code=201)
def create_note(body: NoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.question_id and db.get(Question, body.question_id) is None:
        raise HTTPException(404, "Question not found")
    note = Note(user_id=user.id, **body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return _serialize(note)


@router.put("/{note_id}")
def update_note(note_id: int, body: NoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    note = _owned(db, user, note_id)
    for k, v in body.model_dump().items():
        setattr(note, k, v)
    db.commit()
    db.refresh(note)
    return _serialize(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, note_id))
    db.commit()
    return Response(status_code=204)


class AINoteIn(BaseModel):
    question_id: int | None = None
    topic: str | None = Field(None, max_length=80)

    @model_validator(mode="after")
    def _one_target(self):
        if not (self.question_id or self.topic):
            raise ValueError("Provide question_id or topic")
        return self


@router.post("/ai", status_code=201)
async def generate_ai_note(body: AINoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    await enforce(user.id, "ai-notes", 5)
    solved = False
    if body.question_id:
        q = db.get(Question, body.question_id)
        if q is None:
            raise HTTPException(404, "Question not found")
        uq = db.scalar(
            select(UserQuestion).where(UserQuestion.user_id == user.id, UserQuestion.question_id == q.id)
        )
        solved = bool(uq and uq.status == "solved")
        subject = f"Problem: {q.title} ({q.difficulty}). Topics: {', '.join(t.name for t in q.tags)}"
        title = f"AI notes: {q.title}"
    else:
        subject = f"Topic: {body.topic}"
        title = f"AI notes: {body.topic}"
    code_rule = (
        "Short code snippets are allowed." if solved or not body.question_id
        else "The student has NOT solved this yet: describe the idea only, no code and no full algorithm."
    )
    content = await ai.chat(ai.NOTES_PROMPT.format(code_rule=code_rule), [{"role": "user", "content": subject}], 1200)
    note = Note(user_id=user.id, kind="ai", title=title, content=content, question_id=body.question_id, topic=body.topic)
    db.add(note)
    db.commit()
    db.refresh(note)
    return _serialize(note)
