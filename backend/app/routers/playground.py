from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import current_user
from ..models import User
from ..services import ai, code_tools
from ..services.judge0 import run_code
from ..services.ratelimit import enforce

router = APIRouter(prefix="/playground", tags=["playground"])

Language = Literal["cpp", "java", "python", "javascript", "go"]


class RunIn(BaseModel):
    language: Language
    code: str = Field(min_length=1, max_length=50_000)
    stdin: str = Field("", max_length=10_000)


class ReviewIn(BaseModel):
    language: Language
    code: str = Field(min_length=1, max_length=20_000)


def _numbered(code: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(code.splitlines(), 1))


@router.post("/run")
async def run(body: RunIn, user: User = Depends(current_user)):
    await enforce(user.id, "run", 20)
    return await run_code(body.language, body.code, body.stdin)


@router.post("/review")
async def review(body: ReviewIn, user: User = Depends(current_user)):
    await enforce(user.id, "review", 10)
    if not ai.configured():
        return {**code_tools.review(body.language, body.code), "mode": "rules"}
    result = await ai.complete_json(ai.REVIEW_PROMPT, f"Language: {body.language}\nCode (line-numbered):\n{_numbered(body.code)}")
    return {**result, "mode": "ai"}


@router.post("/dry-run")
async def dry_run(body: RunIn, user: User = Depends(current_user)):
    await enforce(user.id, "dry-run", 10)
    if body.language == "python":
        return await code_tools.trace_python(body.code, body.stdin)
    if not ai.configured():
        raise HTTPException(400, "Without an AI key, Dry run supports Python (real line-by-line trace). "
                                 "Add an AI key in backend/.env to simulate other languages.")
    result = await ai.complete_json(
        ai.DRY_RUN_PROMPT,
        f"Language: {body.language}\nInput:\n{body.stdin}\nCode (line-numbered):\n{_numbered(body.code)}",
        3000,
    )
    return {"steps": result.get("steps", [])[:60], "final_output": result.get("final_output"), "mode": "ai"}
