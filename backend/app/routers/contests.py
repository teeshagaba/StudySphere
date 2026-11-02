from fastapi import APIRouter, Depends

from ..auth import current_user
from ..models import User
from ..services.contests import PLATFORMS, get_contests, user_contest_stats

router = APIRouter(prefix="/contests", tags=["contests"])


@router.get("")
async def list_contests(platform: str | None = None, _: User = Depends(current_user)):
    contests = await get_contests()
    if platform:
        contests = [c for c in contests if c["platform"].lower() == platform.lower()]
    return contests


@router.get("/platforms")
def platforms(_: User = Depends(current_user)):
    return PLATFORMS


@router.get("/stats")
async def stats(user: User = Depends(current_user)):
    return await user_contest_stats(user.codeforces_handle, user.leetcode_handle)
