import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (register tables)
from .config import settings
from .db import Base, SessionLocal, engine
from .routers import (
    analytics, auth, career, companies, contests, dsa, focus, interview, jobs, learning, mentor, notes, playground,
    resources, revision,
)
from .seed import seed
from .services.jobs import get_jobs

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Use Alembic migrations for production schema changes.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    warmup = asyncio.create_task(get_jobs())
    yield
    warmup.cancel()


app = FastAPI(title="StudySphere API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

for module in (
    auth, dsa, revision, notes, career, focus, learning, companies, contests, mentor, playground, analytics, jobs,
    resources, interview,
):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
