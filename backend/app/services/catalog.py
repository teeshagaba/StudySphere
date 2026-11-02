"""Canonical question catalog: resolves any sheet entry to a single Question row."""

import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Question, QuestionAlias, QuestionCompany, Tag

_LC_RE = re.compile(r"leetcode\.com/problems/([a-z0-9-]+)")
_PLATFORMS = {
    "leetcode.com": "LeetCode",
    "geeksforgeeks.org": "GeeksforGeeks",
    "codeforces.com": "Codeforces",
    "codechef.com": "CodeChef",
    "naukri.com": "Code360",
    "codingninjas.com": "Code360",
    "hackerrank.com": "HackerRank",
    "interviewbit.com": "InterviewBit",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:200]


def normalize_url(url: str) -> str:
    p = urlparse(url.strip().lower())
    host = p.netloc.removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}"[:500]


def canonical_slug(title: str, url: str | None, explicit: str | None) -> str:
    if explicit:
        return slugify(explicit)
    if url and (m := _LC_RE.search(url.lower())):
        return m.group(1)
    return slugify(title)


def detect_platform(url: str | None) -> str:
    if not url:
        return "Other"
    host = urlparse(url.lower()).netloc.removeprefix("www.")
    return next((name for domain, name in _PLATFORMS.items() if host.endswith(domain)), "Other")


def get_or_create_tag(db: Session, name: str, kind: str) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.name == name, Tag.kind == kind))
    if tag is None:
        tag = Tag(name=name, kind=kind)
        db.add(tag)
        db.flush()
    return tag


def get_or_create_company(db: Session, name: str) -> Company:
    company = db.scalar(select(Company).where(Company.name == name))
    if company is None:
        company = Company(name=name)
        db.add(company)
        db.flush()
    return company


def upsert_question(
    db: Session,
    *,
    title: str,
    difficulty: str,
    url: str | None = None,
    topics: list[str] = (),
    patterns: list[str] = (),
    companies: dict[str, int] | None = None,
    slug: str | None = None,
) -> Question:
    question = None
    if url and (alias := db.get(QuestionAlias, normalize_url(url))):
        question = db.get(Question, alias.question_id)

    if question is None:
        question = db.scalar(select(Question).where(Question.slug == canonical_slug(title, url, slug)))

    if question is None:
        question = Question(
            slug=canonical_slug(title, url, slug),
            title=title,
            difficulty=difficulty,
            url=url or "",
            platform=detect_platform(url),
        )
        question.tags = []
        question.companies = []
        db.add(question)
        db.flush()

    have = {(t.name, t.kind) for t in question.tags}
    for name, kind in [*((t, "topic") for t in topics), *((p, "pattern") for p in patterns)]:
        if (name, kind) not in have:
            question.tags.append(get_or_create_tag(db, name, kind))
            have.add((name, kind))

    by_company = {qc.company.name: qc for qc in question.companies}
    for name, freq in (companies or {}).items():
        if name in by_company:
            by_company[name].frequency = max(by_company[name].frequency, freq)
        else:
            question.companies.append(QuestionCompany(company=get_or_create_company(db, name), frequency=freq))

    if url:
        key = normalize_url(url)
        if db.get(QuestionAlias, key) is None:
            db.add(QuestionAlias(url=key, question_id=question.id))
    db.flush()
    return question
