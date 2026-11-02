from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from ..config import settings

# Judge0 CE language ids
LANGUAGE_IDS = {"cpp": 54, "java": 62, "python": 71, "javascript": 63, "go": 60}


def _headers(url: str) -> dict[str, str]:
    if not settings.judge0_api_key or url != settings.judge0_url:
        return {}
    host = urlparse(url).netloc
    if host.endswith("rapidapi.com"):
        return {"X-RapidAPI-Key": settings.judge0_api_key, "X-RapidAPI-Host": host}
    return {"X-Auth-Token": settings.judge0_api_key}


async def _submit(client: httpx.AsyncClient, url: str, payload: dict) -> dict:
    r = await client.post(
        f"{url.rstrip('/')}/submissions",
        params={"base64_encoded": "false", "wait": "true"},
        json=payload,
        headers=_headers(url),
    )
    r.raise_for_status()
    return r.json()


async def run_code(language: str, code: str, stdin: str) -> dict:
    payload = {
        "source_code": code,
        "language_id": LANGUAGE_IDS[language],
        "stdin": stdin,
        "cpu_time_limit": 5,
        "wall_time_limit": 10,
        "memory_limit": 256000,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            data = await _submit(client, settings.judge0_url, payload)
        except httpx.HTTPError as e:
            if not settings.judge0_fallback_url:
                raise HTTPException(502, "Code execution service unavailable") from e
            try:
                data = await _submit(client, settings.judge0_fallback_url, payload)
            except httpx.HTTPStatusError as e2:
                if e2.response.status_code == 429:
                    raise HTTPException(429, "Too many runs on the free code runner — wait a minute and try again") from e2
                raise HTTPException(502, "Code execution service unavailable") from e2
            except httpx.HTTPError as e2:
                raise HTTPException(502, "Code execution service unavailable") from e2
    return {
        "status": (data.get("status") or {}).get("description"),
        "stdout": data.get("stdout"),
        "stderr": data.get("stderr"),
        "compile_output": data.get("compile_output"),
        "time": data.get("time"),
        "memory": data.get("memory"),
    }
