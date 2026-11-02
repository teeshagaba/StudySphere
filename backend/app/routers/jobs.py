from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..data.companies import COMPANY_PROFILES, MORE_COMPANIES
from ..db import get_db
from ..models import Application, User
from ..services.jobs import get_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

Level = Literal["intern", "entry", "mid", "senior"]


@router.get("")
async def list_jobs(
    q: str | None = Query(None, max_length=100),
    company: str | None = Query(None, max_length=120),
    level: Level | None = None,
    remote: bool | None = None,
    india: bool | None = None,
    fresher: bool | None = None,
    limit: int = Query(200, ge=1, le=500),
    _: User = Depends(current_user),
):
    jobs = await get_jobs()
    counts: dict[str, int] = {}
    for j in jobs:
        counts[j["company"]] = counts.get(j["company"], 0) + 1
    if q:
        needle = q.lower()
        jobs = [j for j in jobs if needle in j["title"].lower() or needle in j["company"].lower()
                or needle in j["location"].lower() or any(needle in t.lower() for t in j["tags"])]
    if company:
        jobs = [j for j in jobs if j["company"].lower() == company.lower()]
    if level:
        jobs = [j for j in jobs if j["level"] == level]
    if fresher:
        jobs = [j for j in jobs if j["level"] in ("intern", "entry")]
    if remote is not None:
        jobs = [j for j in jobs if j["remote"] == remote]
    if india is not None:
        jobs = [j for j in jobs if j.get("india", False) == india]
    return {
        "total": len(jobs),
        "items": jobs[:limit],
        "companies": sorted(({"name": k, "count": v} for k, v in counts.items()), key=lambda c: -c["count"]),
    }


@router.get("/companies")
async def companies(_: User = Depends(current_user)):
    jobs = await get_jobs()
    by_company: dict[str, list[dict]] = {}
    for j in jobs:
        by_company.setdefault(j["company"].lower(), []).append(j)

    def entry(name: str, profile: dict) -> dict:
        own = sorted(by_company.get(name.lower(), []), key=lambda j: (not j.get("india"), j["level"] == "senior"))
        return {
            "name": name,
            "careers": profile.get("careers") or f"https://www.google.com/search?q={quote(name + ' careers software engineer')}",
            "roles": profile.get("roles", []),
            "process": profile.get("process", []),
            "focus": profile.get("focus", []),
            "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={quote(name + ' software engineer')}",
            "open_roles": len(own),
            "india_roles": sum(1 for j in own if j.get("india")),
            "recent": own[:5],
            "featured": name in COMPANY_PROFILES,
        }

    out = [entry(n, p) for n, p in COMPANY_PROFILES.items()]
    out += [entry(n, {"careers": url}) for n, url in MORE_COMPANIES.items() if n not in COMPANY_PROFILES]
    known = {c["name"].lower() for c in out}
    feed_only = sorted({j["company"] for j in jobs if j["company"].lower() not in known and j["source"] in ("Greenhouse", "Lever")})
    out += [entry(n, {}) for n in feed_only]
    return out


class TrackIn(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    url: HttpUrl


@router.post("/track", status_code=201)
def track(body: TrackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Records an application in the career tracker when the user applies on the original site."""
    url = str(body.url)[:500]
    existing = db.scalar(select(Application).where(Application.user_id == user.id, Application.link == url))
    if existing:
        return {"id": existing.id, "created": False}
    app = Application(
        user_id=user.id, company=body.company[:120], role=body.role[:120], status="applied",
        applied_on=date.today(), link=url, notes="Applied via StudySphere jobs board.",
    )
    db.add(app)
    db.commit()
    return {"id": app.id, "created": True}


@router.get("/tracked")
def tracked(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [link for link in db.scalars(
        select(Application.link).where(Application.user_id == user.id, Application.link.is_not(None))
    )]
