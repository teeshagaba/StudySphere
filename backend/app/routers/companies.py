from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import User
from ..services.mastery import company_readiness, knowledge_graph

router = APIRouter(tags=["companies"])


@router.get("/companies/readiness")
def readiness(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return company_readiness(db, user.id)


@router.get("/knowledge-graph")
def graph(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return knowledge_graph(db, user.id)
