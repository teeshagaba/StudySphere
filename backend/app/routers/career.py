import re
from datetime import date
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Application, User
from ..services.jobs import cached_jobs

router = APIRouter(prefix="/career", tags=["career"])

STATUSES = ("applied", "oa", "interview", "offer", "rejected")
AppStatus = Literal["applied", "oa", "interview", "offer", "rejected"]


class ApplicationIn(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    status: AppStatus = "applied"
    applied_on: date | None = None
    next_step_on: date | None = None
    link: HttpUrl | None = None
    notes: str = Field("", max_length=10_000)


def _serialize(a: Application) -> dict:
    return {
        "id": a.id,
        "company": a.company,
        "role": a.role,
        "status": a.status,
        "applied_on": a.applied_on.isoformat() if a.applied_on else None,
        "next_step_on": a.next_step_on.isoformat() if a.next_step_on else None,
        "link": a.link,
        "notes": a.notes,
    }


def _owned(db: Session, user: User, app_id: int) -> Application:
    app = db.get(Application, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(404, "Application not found")
    return app


def _apply(app: Application, body: ApplicationIn) -> None:
    data = body.model_dump()
    data["link"] = str(body.link) if body.link else None
    for k, v in data.items():
        setattr(app, k, v)


@router.get("")
def list_applications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    apps = db.scalars(select(Application).where(Application.user_id == user.id).order_by(Application.updated_at.desc()))
    return [_serialize(a) for a in apps]


@router.get("/funnel")
def funnel(user: User = Depends(current_user), db: Session = Depends(get_db)):
    counts = dict(
        db.execute(
            select(Application.status, func.count()).where(Application.user_id == user.id).group_by(Application.status)
        ).all()
    )
    return {s: counts.get(s, 0) for s in STATUSES}


@router.post("", status_code=201)
def create_application(body: ApplicationIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    app = Application(user_id=user.id)
    _apply(app, body)
    db.add(app)
    db.commit()
    return _serialize(app)


@router.put("/{app_id}")
def update_application(
    app_id: int, body: ApplicationIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    app = _owned(db, user, app_id)
    _apply(app, body)
    db.commit()
    return _serialize(app)


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, app_id))
    db.commit()
    return Response(status_code=204)


_HOSTS = {
    "amazon.jobs": "Amazon", "metacareers.com": "Meta", "jobs.apple.com": "Apple", "careers.google.com": "Google",
    "google.com": "Google", "careers.microsoft.com": "Microsoft", "jobs.careers.microsoft.com": "Microsoft",
    "apply.careers.microsoft.com": "Microsoft", "jobs.netflix.com": "Netflix", "explore.jobs.netflix.net": "Netflix",
}
_JOB_BOARDS = ("linkedin.com", "naukri.com", "indeed.com", "glassdoor", "wellfound.com", "instahyre.com",
               "cutshort.io", "internshala.com", "unstop.com", "foundit.in", "hirist")


def _guess(url: str, title: str) -> tuple[str, str]:
    """Best-effort (company, role) from a job URL and its page title."""
    p = urlparse(url)
    host = p.netloc.lower().removeprefix("www.")
    parts = [s for s in p.path.split("/") if s]
    company = ""
    if "greenhouse.io" in host or host == "jobs.lever.co" or host.endswith("ashbyhq.com"):
        company = parts[0] if parts else ""
    elif ".myworkdayjobs.com" in host:
        company = host.split(".")[0]
    elif host in _HOSTS:
        company = _HOSTS[host]
    elif not any(b in host for b in _JOB_BOARDS):
        labels = host.split(".")
        company = labels[-2] if len(labels) >= 2 else host
        if company in ("careers", "jobs") and len(labels) >= 3:
            company = labels[-3]

    role = ""
    t = re.sub(r"\s*[|–—]\s*(LinkedIn|Naukri\.com|Indeed.*|Glassdoor.*|Wellfound.*)$", "", title.strip(), flags=re.I)
    if m := re.match(r"(.+?) hiring (.+?)(?: in .+)?$", t):
        company, role = company or m.group(1), m.group(2)
    elif m := re.match(r"(.+?) at (.+)$", t):
        role, company = m.group(1), company or m.group(2)
    elif " - " in t:
        bits = [b.strip() for b in t.split(" - ")]
        role = bits[0]
        company = company or (bits[1] if len(bits) > 1 else "")
    else:
        role = t
    company = company.replace("-", " ").strip() or host
    company = company if any(c.isupper() for c in company) else company.title()
    return company[:120], (role.strip() or "Software role")[:120]


class QuickIn(BaseModel):
    url: HttpUrl
    title: str = Field("", max_length=300)
    status: AppStatus = "applied"


async def _quick_add(db: Session, user: User, body: QuickIn) -> tuple[Application, bool]:
    url = str(body.url)[:500]
    existing = db.scalar(select(Application).where(Application.user_id == user.id, Application.link == url))
    if existing:
        return existing, False
    known = next((j for j in await cached_jobs() if j["url"] == url), None)
    company, role = (known["company"], known["title"][:120]) if known else _guess(url, body.title)
    app = Application(user_id=user.id, company=company, role=role, status=body.status, applied_on=date.today(),
                      link=url, notes="")
    db.add(app)
    return app, True


@router.post("/quick", status_code=201)
async def quick_add(body: QuickIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Track an application from just its link (company/role are detected automatically)."""
    app, created = await _quick_add(db, user, body)
    db.commit()
    return {**_serialize(app), "created": created}


class BulkIn(BaseModel):
    items: list[QuickIn] = Field(min_length=1, max_length=50)


@router.post("/bulk", status_code=201)
async def bulk_add(body: BulkIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    created = 0
    for item in body.items:
        _, new = await _quick_add(db, user, item)
        created += new
        db.flush()
    db.commit()
    return {"created": created, "skipped": len(body.items) - created}
