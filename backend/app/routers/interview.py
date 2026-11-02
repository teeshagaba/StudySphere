from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import InterviewAttempt, User, UserLearning, UserQuestion
from ..services import ai, ai_era
from ..services.ratelimit import enforce
from .learning import TRACKS

router = APIRouter(prefix="/interview", tags=["interview"])

DSA_BENCHMARK = 150  # solving ~150 well-chosen problems ≈ interview-ready DSA


def _best(db: Session, user_id: int) -> dict[str, tuple[int, int]]:
    rows = db.execute(
        select(InterviewAttempt.exercise_id, func.max(InterviewAttempt.score), func.count())
        .where(InterviewAttempt.user_id == user_id)
        .group_by(InterviewAttempt.exercise_id)
    ).all()
    return {eid: (best, n) for eid, best, n in rows}


@router.get("/sections")
def sections(user: User = Depends(current_user), db: Session = Depends(get_db)):
    best = _best(db, user.id)
    out = []
    for sid, title, tagline, skill in ai_era.SECTIONS:
        items = [
            {"id": e["id"], "title": e["title"], "difficulty": e["difficulty"], "minutes": e["minutes"],
             "summary": e["summary"], "best": best.get(e["id"], (None, 0))[0], "attempts": best.get(e["id"], (None, 0))[1]}
            for e in ai_era.EXERCISES.values() if e["section"] == sid
        ]
        done = [i["best"] or 0 for i in items]
        steps, links = ai_era.GUIDES.get(sid, ([], []))
        out.append({"id": sid, "title": title, "tagline": tagline, "skill": skill, "exercises": items,
                    "progress": round(sum(done) / len(done)) if done else 0,
                    "guide": {"steps": steps, "resources": [{"title": t, "url": u} for t, u in links]}})
    return {"sections": out, "ai_grading": ai.configured()}


@router.get("/exercises/{exercise_id}")
def exercise(exercise_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ex = ai_era.get(exercise_id)
    best = _best(db, user.id).get(exercise_id, (None, 0))
    return {**ai_era.public(ex), "best": best[0], "attempts": best[1]}


class SubmitIn(BaseModel):
    answers: dict[str, str | int | list[str] | list[int] | None] = Field(default_factory=dict)
    seconds: int = Field(0, ge=0, le=6 * 3600)


@router.post("/exercises/{exercise_id}/submit")
async def submit(exercise_id: str, body: SubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ex = ai_era.get(exercise_id)
    if ai.configured():
        await enforce(user.id, "interview-grade", 30)
    result = await ai_era.grade(ex, body.answers)
    db.add(InterviewAttempt(user_id=user.id, exercise_id=ex["id"], section=ex["section"], score=result["score"],
                            seconds=body.seconds))
    db.commit()
    best = _best(db, user.id).get(exercise_id, (result["score"], 1))
    return {**result, "best": best[0], "attempts": best[1]}


def _track_pct(rows: dict[tuple[str, str], str], track: str) -> int:
    topics = TRACKS.get(track, [])
    if not topics:
        return 0
    score = sum(1 if rows.get((track, t)) == "done" else 0.5 if rows.get((track, t)) == "learning" else 0 for t in topics)
    return round(100 * score / len(topics))


@router.get("/readiness")
def readiness(user: User = Depends(current_user), db: Session = Depends(get_db)):
    best = {eid: b for eid, (b, _) in _best(db, user.id).items()}

    def skill(sections: set[str]) -> int:
        ids = [e["id"] for e in ai_era.EXERCISES.values() if e["section"] in sections]
        return round(sum(best.get(i, 0) for i in ids) / len(ids)) if ids else 0

    learning = {(r.track, r.topic): r.status for r in db.scalars(select(UserLearning).where(UserLearning.user_id == user.id))}
    solved = db.scalar(select(func.count()).select_from(UserQuestion).where(
        UserQuestion.user_id == user.id, UserQuestion.status == "solved"))

    dsa = min(100, round(100 * solved / DSA_BENCHMARK))
    development = round(sum(_track_pct(learning, t) for t in ("Git", "Docker", "Projects", "SQL")) / 4)
    system_design = round(0.6 * skill(ai_era.SKILL_SECTIONS["system_design"]) + 0.4 * _track_pct(learning, "System Design"))

    fundamentals = {
        "DSA": (dsa, "/dsa"),
        "Operating Systems": (_track_pct(learning, "Operating Systems"), "/learning"),
        "DBMS": (_track_pct(learning, "DBMS"), "/learning"),
        "OOP": (_track_pct(learning, "OOP"), "/learning"),
    }
    engineering = {
        "Development": (development, "/learning"),
        "Code Reading": (skill(ai_era.SKILL_SECTIONS["code_reading"]), "/interview?section=comprehension"),
        "Debugging": (skill(ai_era.SKILL_SECTIONS["debugging"]), "/interview?section=debugging"),
        "AI Collaboration": (skill(ai_era.SKILL_SECTIONS["ai_collab"]), "/interview?section=verify"),
        "System Design": (system_design, "/interview?section=system"),
    }
    fund = sum(v for v, _ in fundamentals.values()) / len(fundamentals)
    eng = sum(v for v, _ in engineering.values()) / len(engineering)
    weakest = sorted([*fundamentals.items(), *engineering.items()], key=lambda kv: kv[1][0])[:3]
    return {
        "readiness": round(0.3 * fund + 0.7 * eng),
        "split": {"fundamentals": {"weight": 30, "score": round(fund)}, "engineering": {"weight": 70, "score": round(eng)}},
        "fundamentals": [{"name": k, "score": v, "href": h} for k, (v, h) in fundamentals.items()],
        "engineering": [{"name": k, "score": v, "href": h} for k, (v, h) in engineering.items()],
        "skills": {
            "DSA Progress": dsa,
            "Development Progress": development,
            "Debugging Skill": engineering["Debugging"][0],
            "Code Reading Skill": engineering["Code Reading"][0],
            "AI Collaboration Skill": engineering["AI Collaboration"][0],
            "System Design Skill": system_design,
        },
        "next_steps": [{"name": k, "score": v, "href": h} for k, (v, h) in weakest],
    }
