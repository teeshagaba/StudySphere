"""Contest aggregator. Direct APIs for LeetCode/Codeforces/CodeChef; clist.by (optional key) for the rest."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from redis.exceptions import RedisError

from ..cache import redis
from ..config import settings

log = logging.getLogger(__name__)
CACHE_KEY = "contests:v1"
CACHE_TTL_SECONDS = 1800

CLIST_HOSTS = {
    "codeforces.com": "Codeforces",
    "leetcode.com": "LeetCode",
    "codechef.com": "CodeChef",
    "atcoder.jp": "AtCoder",
    "hackerrank.com": "HackerRank",
    "hackerearth.com": "HackerEarth",
    "topcoder.com": "TopCoder",
    "codesignal.com": "CodeSignal",
    "kaggle.com": "Kaggle",
    "geeksforgeeks.org": "GeeksforGeeks",
    "naukri.com/code360": "Code360",
    "codingame.com": "CodinGame",
    "projecteuler.net": "Project Euler",
    "yukicoder.me": "yukicoder",
    "toph.co": "Toph",
    "dmoj.ca": "DMOJ",
    "ctftime.org": "CTFtime",
    "devfolio.co": "Devfolio",
    "unstop.com": "Unstop",
}
PLATFORMS = sorted(set(CLIST_HOSTS.values()))


def _contest(platform: str, name: str, url: str, start: datetime, duration_min: int) -> dict | None:
    if not url.startswith(("https://", "http://")):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return {
        "platform": platform,
        "name": name.strip(),
        "url": url,
        "start": start.astimezone(timezone.utc).isoformat(),
        "duration_min": int(duration_min),
    }


async def _codeforces(client: httpx.AsyncClient) -> list[dict | None]:
    r = await client.get("https://codeforces.com/api/contest.list", params={"gym": "false"})
    r.raise_for_status()
    return [
        _contest(
            "Codeforces",
            c["name"],
            f"https://codeforces.com/contests/{c['id']}",
            datetime.fromtimestamp(c["startTimeSeconds"], tz=timezone.utc),
            c["durationSeconds"] // 60,
        )
        for c in r.json()["result"]
        if c.get("phase") == "BEFORE" and "startTimeSeconds" in c
    ]


async def _leetcode(client: httpx.AsyncClient) -> list[dict | None]:
    r = await client.post(
        "https://leetcode.com/graphql",
        json={"query": "query { upcomingContests { title titleSlug startTime duration } }"},
        headers={"Referer": "https://leetcode.com/contest/"},
    )
    r.raise_for_status()
    return [
        _contest(
            "LeetCode",
            c["title"],
            f"https://leetcode.com/contest/{c['titleSlug']}",
            datetime.fromtimestamp(c["startTime"], tz=timezone.utc),
            c["duration"] // 60,
        )
        for c in r.json()["data"]["upcomingContests"]
    ]


async def _codechef(client: httpx.AsyncClient) -> list[dict | None]:
    r = await client.get(
        "https://www.codechef.com/api/list/contests/all",
        params={"sort_by": "START", "sorting_order": "asc", "offset": 0, "mode": "all"},
    )
    r.raise_for_status()
    data = r.json()
    return [
        _contest(
            "CodeChef",
            c["contest_name"],
            f"https://www.codechef.com/{c['contest_code']}",
            datetime.fromisoformat(c["contest_start_date_iso"]),
            int(c["contest_duration"]),
        )
        for c in data.get("present_contests", []) + data.get("future_contests", [])
    ]


async def _clist(client: httpx.AsyncClient) -> list[dict | None]:
    if not (settings.clist_username and settings.clist_api_key):
        return []
    r = await client.get(
        "https://clist.by/api/v4/contest/",
        params={"upcoming": "true", "order_by": "start", "limit": 500, "format": "json"},
        headers={"Authorization": f"ApiKey {settings.clist_username}:{settings.clist_api_key}"},
    )
    r.raise_for_status()
    out = []
    for c in r.json().get("objects", []):
        platform = CLIST_HOSTS.get(c.get("resource", ""))
        if platform:
            out.append(
                _contest(platform, c["event"], c["href"], datetime.fromisoformat(c["start"]), c["duration"] // 60)
            )
    return out


FETCHERS = [_codeforces, _leetcode, _codechef, _clist]


async def fetch_all() -> list[dict]:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "StudyOS/0.1"}) as client:
        results = await asyncio.gather(*(f(client) for f in FETCHERS), return_exceptions=True)

    now = datetime.now(timezone.utc)
    seen: set[tuple] = set()
    contests: list[dict] = []
    for fetcher, result in zip(FETCHERS, results):
        if isinstance(result, Exception):
            log.warning("Contest fetcher %s failed: %s", fetcher.__name__, result)
            continue
        for c in result:
            if c is None:
                continue
            keys = {(c["platform"], c["name"].lower()), (c["platform"], c["start"])}
            if keys & seen:
                continue
            if datetime.fromisoformat(c["start"]) + timedelta(minutes=c["duration_min"]) < now:
                continue
            seen |= keys
            contests.append(c)
    return sorted(contests, key=lambda c: c["start"])


async def get_contests() -> list[dict]:
    try:
        if cached := await redis.get(CACHE_KEY):
            return json.loads(cached)
    except RedisError as e:
        log.warning("Redis unavailable: %s", e)
    contests = await fetch_all()
    if contests:
        try:
            await redis.set(CACHE_KEY, json.dumps(contests), ex=CACHE_TTL_SECONDS)
        except RedisError:
            pass
    return contests


async def user_contest_stats(codeforces_handle: str | None, leetcode_handle: str | None) -> dict:
    out: dict = {"codeforces": None, "leetcode": None}
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "StudyOS/0.1"}) as client:
        if codeforces_handle:
            try:
                r = await client.get("https://codeforces.com/api/user.rating", params={"handle": codeforces_handle})
                history = r.json().get("result", []) if r.status_code == 200 else []
                out["codeforces"] = {
                    "rating": history[-1]["newRating"] if history else None,
                    "max_rating": max((h["newRating"] for h in history), default=None),
                    "contests": len(history),
                    "history": [
                        {"name": h["contestName"], "rating": h["newRating"], "rank": h["rank"],
                         "date": datetime.fromtimestamp(h["ratingUpdateTimeSeconds"], tz=timezone.utc).date().isoformat()}
                        for h in history[-30:]
                    ],
                }
            except (httpx.HTTPError, ValueError, KeyError) as e:
                log.warning("Codeforces stats failed: %s", e)
        if leetcode_handle:
            try:
                r = await client.post(
                    "https://leetcode.com/graphql",
                    json={
                        "query": "query($u: String!) { userContestRanking(username: $u) "
                        "{ attendedContestsCount rating globalRanking topPercentage } }",
                        "variables": {"u": leetcode_handle},
                    },
                    headers={"Referer": "https://leetcode.com/"},
                )
                out["leetcode"] = r.json().get("data", {}).get("userContestRanking")
            except (httpx.HTTPError, ValueError) as e:
                log.warning("LeetCode stats failed: %s", e)
    return out
