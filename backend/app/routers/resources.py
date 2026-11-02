from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..data.resources import KINDS, RESOURCES
from ..db import get_db
from ..models import User, UserResource

router = APIRouter(prefix="/resources", tags=["resources"])

Kind = Literal["book", "notes", "cheatsheet", "practice", "course", "video"]


def _mine(r: UserResource) -> dict:
    return {
        "id": r.id, "title": r.title, "author": "You", "kind": r.kind, "url": r.url,
        "tags": [t for t in r.tags.split(",") if t], "description": "", "mine": True,
    }


@router.get("")
def list_resources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    catalog = [
        {"id": None, "title": t, "author": a, "kind": k, "tags": tags, "url": u, "description": d, "mine": False}
        for t, a, k, tags, u, d in RESOURCES
    ]
    mine = db.scalars(select(UserResource).where(UserResource.user_id == user.id).order_by(UserResource.id.desc()))
    return {"kinds": KINDS, "items": [_mine(r) for r in mine] + catalog}


class ResourceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    kind: Kind = "notes"
    url: HttpUrl
    tags: list[str] = Field(default_factory=list, max_length=10)


@router.post("", status_code=201)
def add_resource(body: ResourceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    url = str(body.url)
    if not url.startswith(("https://", "http://")):
        raise HTTPException(422, "Only http(s) links are allowed")
    r = UserResource(
        user_id=user.id, title=body.title.strip(), kind=body.kind, url=url[:500],
        tags=",".join(t.strip().replace(",", " ")[:30] for t in body.tags if t.strip())[:200],
    )
    db.add(r)
    db.commit()
    return _mine(r)


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(UserResource, resource_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(404, "Resource not found")
    db.delete(r)
    db.commit()
    return Response(status_code=204)
