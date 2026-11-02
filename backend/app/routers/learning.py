from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..data.lessons import LESSONS, TRACK_RESOURCES
from ..db import get_db
from ..models import User, UserLearning
from ..services.gamification import LEARNING_XP, award_xp, check_badges

router = APIRouter(prefix="/learning", tags=["learning"])

TRACKS: dict[str, list[str]] = {
    "Python": ["Syntax & Data Types", "OOP", "Iterators & Generators", "Decorators", "Async IO", "Typing", "Testing"],
    "SQL": ["SELECT & Filtering", "Joins", "Aggregation", "Window Functions", "CTEs", "Indexes", "Query Plans"],
    "Machine Learning": ["Linear Regression", "Logistic Regression", "Trees & Ensembles", "SVM", "Clustering",
                         "Feature Engineering", "Model Evaluation"],
    "Deep Learning": ["Neural Nets & Backprop", "CNNs", "RNNs & LSTMs", "Attention", "Transformers",
                      "Regularization", "PyTorch"],
    "LLMs": ["Tokenization", "Embeddings", "Prompt Engineering", "Fine-tuning", "LoRA / PEFT", "Evaluation",
             "Safety & Guardrails"],
    "RAG": ["Chunking", "Vector Databases", "Retrieval Strategies", "Hybrid Search", "Re-ranking", "RAG Evaluation"],
    "Agents": ["Tool Calling", "ReAct", "Planning", "Memory", "Multi-agent Systems", "Agent Evaluation"],
    "MCP": ["MCP Architecture", "Servers", "Clients", "Tools", "Resources & Prompts", "Security"],
    "Azure AI": ["Azure OpenAI", "AI Search", "AI Foundry", "Content Safety", "Prompt Flow", "Deployment & Monitoring"],
    "System Design": ["Scalability Basics", "Load Balancing", "Caching", "Databases & Sharding", "Message Queues",
                      "Consistency & CAP", "Rate Limiting", "Designing Feeds", "Designing Chat"],
    "Operating Systems": ["Processes & Threads", "CPU Scheduling", "Synchronization & Deadlocks", "Memory & Paging",
                          "Virtual Memory", "File Systems", "I/O & Interrupts"],
    "DBMS": ["ER Model & Normalization", "SQL & Joins", "Indexing (B+ Trees)", "Transactions & ACID",
             "Isolation Levels", "Concurrency Control", "Query Optimization"],
    "OOP": ["Classes & Objects", "Encapsulation", "Inheritance & Polymorphism", "Abstraction & Interfaces",
            "SOLID Principles", "Design Patterns", "Composition over Inheritance"],
    "Git": ["Commits & Branching", "Merge vs Rebase", "Resolving Conflicts", "Pull Request Workflow",
            "Bisect & Blame", "Undoing Changes (reset/revert)"],
    "Docker": ["Images & Containers", "Writing Dockerfiles", "Multi-stage Builds", "Volumes & Networking",
               "Docker Compose", "Image Security & Size"],
    "Projects": ["CRUD REST API", "Authentication (JWT/OAuth)", "Database Migrations", "Automated Tests",
                 "CI/CD Pipeline", "Deploy to Cloud", "Logging & Monitoring"],
}

LearnStatus = Literal["not_started", "learning", "done"]


@router.get("")
def tracks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    status = {
        (r.track, r.topic): r.status for r in db.scalars(select(UserLearning).where(UserLearning.user_id == user.id))
    }
    out = []
    for track, topics in TRACKS.items():
        items = []
        for t in topics:
            points, practice = LESSONS.get(track, {}).get(t, ([], ""))
            items.append({"name": t, "status": status.get((track, t), "not_started"), "points": points, "practice": practice})
        done = sum(1 for i in items if i["status"] == "done")
        learning = sum(1 for i in items if i["status"] == "learning")
        out.append({
            "track": track, "topics": items, "progress": round((done + 0.5 * learning) / len(items) * 100),
            "resources": [{"title": title, "url": url} for title, url in TRACK_RESOURCES.get(track, [])],
        })
    return out


class LearnIn(BaseModel):
    track: str
    topic: str
    status: LearnStatus


@router.put("")
def set_status(body: LearnIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.topic not in TRACKS.get(body.track, []):
        raise HTTPException(404, "Unknown track or topic")
    row = db.scalar(
        select(UserLearning).where(
            UserLearning.user_id == user.id, UserLearning.track == body.track, UserLearning.topic == body.topic
        )
    )
    if row is None:
        row = UserLearning(user_id=user.id, track=body.track, topic=body.topic, status="not_started")
        db.add(row)
    xp = 0
    if body.status == "done" and row.status != "done":
        xp = LEARNING_XP
        award_xp(db, user, f"learn:{body.track}", xp)
    row.status = body.status
    new_badges = check_badges(db, user)
    db.commit()
    return {"track": body.track, "topic": body.topic, "status": row.status, "xp_gained": xp, "new_badges": new_badges}
