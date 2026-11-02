from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Question, RevisionItem, User, UserQuestion
from ..services import ai, offline_mentor
from ..services.mastery import company_readiness, topic_mastery
from ..services.ratelimit import enforce

router = APIRouter(prefix="/mentor", tags=["mentor"])

Mode = Literal["hint", "teacher", "interviewer", "debugger", "planner"]
UNLOCK_MIN_ATTEMPTS = 2
UNLOCK_MIN_MINUTES = 30


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatIn(BaseModel):
    mode: Mode
    messages: list[Message] = Field(min_length=1, max_length=30)
    question_id: int | None = None
    code: str | None = Field(None, max_length=20_000)
    hint_level: int = Field(1, ge=1, le=3)
    reveal: bool = False


def _planner_context(db: Session, user: User) -> str:
    mastery = [m for m in topic_mastery(db, user.id) if m["total"]]
    weak = ", ".join(f"{m['topic']} ({m['mastery']}%)" for m in sorted(mastery, key=lambda m: m["mastery"])[:5])
    due = db.scalar(
        select(func.count()).select_from(RevisionItem).where(
            RevisionItem.user_id == user.id, RevisionItem.completed.is_(False), RevisionItem.due_on <= date.today()
        )
    )
    companies = ", ".join(f"{c['company']} {c['readiness']}%" for c in company_readiness(db, user.id)[:5])
    return (
        f"Today is {date.today().isoformat()}. Weakest topics: {weak or 'n/a'}. "
        f"Revisions due today: {due}. Company readiness: {companies or 'n/a'}."
    )


@router.post("/chat")
async def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    await enforce(user.id, "mentor", 20)
    system = [ai.BASE_PROMPT, ai.MODE_PROMPTS[body.mode]]
    unlocked = False
    q = None

    if body.question_id:
        q = db.get(Question, body.question_id)
        if q is None:
            raise HTTPException(404, "Question not found")
        uq = db.scalar(
            select(UserQuestion).where(UserQuestion.user_id == user.id, UserQuestion.question_id == q.id)
        )
        system.append(
            f"Current problem: {q.title} ({q.difficulty}). Topics: {', '.join(t.name for t in q.tags)}. URL: {q.url}"
        )
        if body.reveal and uq and (
            uq.status == "solved" or uq.attempts >= UNLOCK_MIN_ATTEMPTS or uq.time_spent_min >= UNLOCK_MIN_MINUTES
        ):
            unlocked = True
            system.append(ai.SOLUTION_UNLOCKED)
    if body.mode == "hint":
        system.append(f"Requested hint level: {body.hint_level}.")
    if body.mode == "planner":
        system.append(_planner_context(db, user))

    messages = [m.model_dump() for m in body.messages]
    if not ai.configured():
        planner = _planner_context(db, user) if body.mode == "planner" else ""
        text = offline_mentor.reply(body.mode, q, body.hint_level, messages[-1]["content"], planner)
        return {"reply": text, "solution_unlocked": False, "reveal_blocked": body.reveal, "offline": True}
    if body.code:
        messages.insert(0, {"role": "user", "content": f"My current code:\n```\n{body.code}\n```"})

    reply = await ai.chat("\n\n".join(system), messages)
    return {
        "reply": reply,
        "solution_unlocked": unlocked,
        "reveal_blocked": body.reveal and not unlocked,
        "offline": False,
    }


class HintIn(BaseModel):
    question_id: int
    level: int = Field(1, ge=1, le=3)


@router.post("/hint")
async def hint(body: HintIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """One progressive hint for a problem: 1 = nudge, 2 = pattern, 3 = step outline."""
    await enforce(user.id, "mentor", 20)
    q = db.get(Question, body.question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    if not ai.configured():
        return {"hint": offline_mentor.reply("hint", q, body.level, "").replace(offline_mentor.FOOTER, ""),
                "level": body.level, "offline": True}
    system = "\n\n".join([
        ai.BASE_PROMPT, ai.MODE_PROMPTS["hint"], f"Requested hint level: {body.level}.",
        f"Problem: {q.title} ({q.difficulty}). Tags: {', '.join(t.name for t in q.tags)}. URL: {q.url}",
    ])
    text = await ai.chat(system, [{"role": "user", "content": f"Give me hint level {body.level} for {q.title}."}], 300)
    return {"hint": text, "level": body.level, "offline": False}
