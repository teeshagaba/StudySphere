"""Job aggregator over public job-board APIs. Apply links always point to the original posting."""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
from redis.exceptions import RedisError

from ..cache import redis
from ..data.companies import EIGHTFOLD_SITES, GREENHOUSE_BOARDS, LEVER_BOARDS, WORKDAY_SITES

log = logging.getLogger(__name__)
CACHE_KEY = "jobs:v2"
CACHE_TTL_SECONDS = 3600
PER_COMPANY_CAP = 60
FETCH_DEADLINE_SECONDS = 20

_TECH = re.compile(
    r"engineer|developer|\bsde\b|software|data|machine learning|\bml\b|\bai\b|backend|frontend|full[- ]?stack"
    r"|devops|\bsre\b|security|platform|infrastructure|mobile|android|\bios\b|scientist",
    re.I,
)
_INTERN = re.compile(r"intern|apprentice|co-?op|trainee", re.I)
_SENIOR = re.compile(r"senior|\bsr\b|staff|principal|lead|manager|director|head|architect|\b(pmts|smts|lmts)\b|\b(iii|iv|3|4)\b", re.I)
_MID = re.compile(r"\b(ii|2)\b|sde[- ]?2|sde[- ]?ii|mid[- ]level", re.I)
_INDIA = re.compile(
    r"india|\bIND\b|bengaluru|bangalore|hyderabad|pune|gurgaon|gurugram|noida|mumbai|chennai|delhi|kolkata"
    r"|ahmedabad|kochi|coimbatore|jaipur|chandigarh|thiruvananthapuram",
    re.I,
)


def _level(title: str) -> str:
    if _INTERN.search(title):
        return "intern"
    if _SENIOR.search(title):
        return "senior"
    if _MID.search(title):
        return "mid"
    return "entry"


def _job(source: str, company: str, title: str, url: str, location: str, posted: str | None, tags=()) -> dict | None:
    if not url.startswith("https://") or not _TECH.search(title):
        return None
    location = (location or "").strip() or "Unspecified"
    return {
        "id": hashlib.sha1(url.encode()).hexdigest()[:16],
        "company": company.strip(),
        "title": title.strip(),
        "location": location[:120],
        "remote": "remote" in location.lower() or "anywhere" in location.lower(),
        "india": bool(_INDIA.search(location)),
        "url": url,
        "source": source,
        "posted_at": posted,
        "level": _level(title),
        "tags": [str(t)[:30] for t in list(tags)[:6]],
    }


async def _greenhouse(client: httpx.AsyncClient, token: str, company: str) -> list[dict | None]:
    r = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    r.raise_for_status()
    return [
        _job("Greenhouse", company, j["title"], j["absolute_url"], (j.get("location") or {}).get("name", ""),
             j.get("updated_at"))
        for j in r.json().get("jobs", [])
    ]


async def _lever(client: httpx.AsyncClient, token: str, company: str) -> list[dict | None]:
    r = await client.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"})
    r.raise_for_status()
    out = []
    for j in r.json():
        cats = j.get("categories") or {}
        posted = datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).isoformat() if j.get("createdAt") else None
        out.append(_job("Lever", company, j.get("text", ""), j.get("hostedUrl", ""), cats.get("location", ""), posted,
                        [t for t in (cats.get("team"), cats.get("commitment")) if t]))
    return out


async def _remotive(client: httpx.AsyncClient) -> list[dict | None]:
    r = await client.get("https://remotive.com/api/remote-jobs", params={"category": "software-dev", "limit": 150})
    r.raise_for_status()
    return [
        _job("Remotive", j["company_name"], j["title"], j["url"],
             f"Remote · {j.get('candidate_required_location') or 'Worldwide'}", j.get("publication_date"),
             j.get("tags", []))
        for j in r.json().get("jobs", [])
    ]


async def _arbeitnow(client: httpx.AsyncClient) -> list[dict | None]:
    r = await client.get("https://www.arbeitnow.com/api/job-board-api")
    r.raise_for_status()
    out = []
    for j in r.json().get("data", []):
        loc = j.get("location", "") + (" · Remote" if j.get("remote") else "")
        posted = datetime.fromtimestamp(j["created_at"], tz=timezone.utc).isoformat() if j.get("created_at") else None
        out.append(_job("Arbeitnow", j["company_name"], j["title"], j["url"], loc, posted, j.get("tags", [])))
    return out


async def _amazon(client: httpx.AsyncClient, location: str) -> list[dict | None]:
    r = await client.get(
        "https://www.amazon.jobs/en/search.json",
        params={"base_query": "software", "loc_query": location, "result_limit": 100, "sort": "recent"},
    )
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        try:
            posted = datetime.strptime(j.get("posted_date", ""), "%B %d, %Y").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            posted = None
        out.append(_job("Amazon Jobs", "Amazon", j.get("title", ""), f"https://www.amazon.jobs{j.get('job_path', '')}",
                        j.get("normalized_location") or j.get("location", ""), posted))
    return out


def _workday_posted(text: str) -> str | None:
    now = datetime.now(timezone.utc)
    t = (text or "").lower()
    if "today" in t:
        return now.isoformat()
    if "yesterday" in t:
        return (now - timedelta(days=1)).isoformat()
    if m := re.search(r"(\d+)", t):
        return (now - timedelta(days=int(m.group(1)))).isoformat()
    return None


async def _workday(client: httpx.AsyncClient, host: str, tenant: str, site: str, company: str) -> list[dict | None]:
    out = []
    for text in ("software India", "software engineer"):
        r = await client.post(
            f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": text},
        )
        r.raise_for_status()
        for j in r.json().get("jobPostings", []):
            out.append(_job("Workday", company, j.get("title", ""), f"https://{host}/en-US/{site}{j.get('externalPath', '')}",
                            j.get("locationsText", ""), _workday_posted(j.get("postedOn", ""))))
    return out


async def _eightfold(client: httpx.AsyncClient, host: str, domain: str, company: str) -> list[dict | None]:
    out = []
    for location in ("India", ""):
        r = await client.get(
            f"https://{host}/api/apply/v2/jobs",
            params={"domain": domain, "query": "software", "location": location, "start": 0, "num": 50},
        )
        r.raise_for_status()
        for j in r.json().get("positions", []):
            url = j.get("canonicalPositionUrl") or f"https://{host}/careers/job/{j.get('id')}"
            posted = datetime.fromtimestamp(j["t_create"], tz=timezone.utc).isoformat() if j.get("t_create") else None
            out.append(_job("Careers site", company, j.get("name", ""), url, j.get("location", ""), posted))
    return out


async def fetch_all() -> list[dict]:
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "StudySphere/1.0"}) as client:
        tasks = [
            *(_greenhouse(client, t, c) for t, c in GREENHOUSE_BOARDS.items()),
            *(_lever(client, t, c) for t, c in LEVER_BOARDS.items()),
            *(_workday(client, h, t, s, c) for (h, t, s), c in WORKDAY_SITES.items()),
            *(_eightfold(client, h, d, c) for (h, d), c in EIGHTFOLD_SITES.items()),
            _amazon(client, "India"),
            _amazon(client, ""),
            _remotive(client),
            _arbeitnow(client),
        ]
        # Stay well under the frontend proxy's 30s limit; slow sources are skipped this round.
        done, pending = await asyncio.wait([asyncio.ensure_future(t) for t in tasks], timeout=FETCH_DEADLINE_SECONDS)
        for task in pending:
            task.cancel()
        if pending:
            log.warning("%d job source(s) timed out", len(pending))

    jobs: list[dict] = []
    seen: set[str] = set()
    for task in done:
        if (exc := task.exception()) is not None:
            log.warning("Job source failed: %r", exc)
            continue
        result = task.result()
        per_company: dict[str, int] = {}
        for j in result:
            if j is None or j["id"] in seen:
                continue
            if not j["india"] and per_company.get(j["company"], 0) >= PER_COMPANY_CAP:
                continue
            per_company[j["company"]] = per_company.get(j["company"], 0) + 1
            seen.add(j["id"])
            jobs.append(j)
    return sorted(jobs, key=lambda j: j["posted_at"] or "", reverse=True)


async def cached_jobs() -> list[dict]:
    try:
        cached = await redis.get(CACHE_KEY)
    except RedisError:
        return []
    return json.loads(cached) if cached else []


_fetch_lock = asyncio.Lock()


async def get_jobs() -> list[dict]:
    if cached := await cached_jobs():
        return cached
    async with _fetch_lock:
        if cached := await cached_jobs():
            return cached
        jobs = await fetch_all()
        if jobs:
            try:
                await redis.set(CACHE_KEY, json.dumps(jobs), ex=CACHE_TTL_SECONDS)
            except RedisError:
                pass
        return jobs
