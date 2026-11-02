"""Syncs the canonical problem bank and curated/company sheets on every startup (idempotent)."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data.sheets import FAANG, FAANG_SHEET, SECTION_ORDER, SHEETS, problems
from .models import Question, Sheet, SheetQuestion
from .services.catalog import slugify, upsert_question

_DIFF_RANK = {"Easy": 0, "Medium": 1, "Hard": 2}


def _section_key(section: str) -> int:
    return SECTION_ORDER.index(section) if section in SECTION_ORDER else len(SECTION_ORDER)


def _sync_sheet(db: Session, slug: str, name: str, desc: str, kind: str, items: list[tuple[str, Question]]) -> None:
    sheet = db.scalar(select(Sheet).where(Sheet.slug == slug))
    if sheet is None:
        sheet = Sheet(slug=slug, name=name, description=desc, kind=kind)
        db.add(sheet)
    sheet.name, sheet.description, sheet.kind = name, desc, kind
    sheet.items.clear()
    db.flush()
    seen: set[int] = set()
    for section, q in items:
        if q.id not in seen:
            seen.add(q.id)
            sheet.items.append(SheetQuestion(question=q, position=len(seen), section=section))


def seed(db: Session) -> None:
    by_sheet: dict[str, list[tuple[str, Question, str]]] = defaultdict(list)
    by_company: dict[str, list[tuple[int, str, Question]]] = defaultdict(list)
    faang: list[tuple[str, Question, str]] = []

    for p in problems():
        q = upsert_question(
            db,
            title=p.title,
            difficulty=p.difficulty,
            url=f"https://leetcode.com/problems/{p.slug}/",
            slug=p.slug,
            topics=p.topics,
            patterns=p.patterns,
            companies=p.companies,
        )
        # Drop stale tag names left over from earlier catalog versions.
        wanted = {(t, "topic") for t in p.topics} | {(t, "pattern") for t in p.patterns}
        q.tags = [t for t in q.tags if (t.name, t.kind) in wanted]
        for code in p.sheets:
            by_sheet[code].append((p.section, q, p.difficulty))
        for company, freq in p.companies.items():
            by_company[company].append((freq, p.section, q))
        if any(p.companies.get(c, 0) >= 4 for c in FAANG):
            faang.append((p.section, q, p.difficulty))

    def ordered(rows: list[tuple[str, Question, str]]) -> list[tuple[str, Question]]:
        rows = sorted(rows, key=lambda r: (_section_key(r[0]), _DIFF_RANK[r[2]]))
        return [(section, q) for section, q, _ in rows]

    for code, (slug, name, desc) in SHEETS.items():
        _sync_sheet(db, slug, name, desc, "curated", ordered(by_sheet[code]))
    _sync_sheet(db, *FAANG_SHEET, "curated", ordered(faang))

    for company, rows in by_company.items():
        rows.sort(key=lambda r: -r[0])
        _sync_sheet(
            db,
            f"company-{slugify(company)}",
            f"{company} Sheet",
            f"Most frequently asked {company} questions, sorted by frequency.",
            "company",
            [(f"Frequency {freq}/5", q) for freq, _, q in rows],
        )
    db.commit()
