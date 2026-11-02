"""Mastery = weighted by difficulty, self-reported confidence and revision stage — not raw solved count."""

from collections import defaultdict
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Question, QuestionCompany, RevisionItem, Tag, UserQuestion, question_tags

DIFF_WEIGHT = {"Easy": 1.0, "Medium": 2.0, "Hard": 3.0}
MASTERY_TARGET = 20.0

PREREQS: dict[str, list[str]] = {
    "String": ["Array"],
    "HashMap": ["Array"],
    "Two Pointers": ["Array"],
    "Sorting": ["Array"],
    "Matrix": ["Array"],
    "Binary Search": ["Array", "Sorting"],
    "Sliding Window": ["Two Pointers", "HashMap"],
    "Stack": ["Array"],
    "Linked List": ["Array"],
    "Tree": ["Linked List", "Stack"],
    "Heap": ["Tree"],
    "Backtracking": ["Tree"],
    "Graph": ["Tree", "HashMap"],
    "Dynamic Programming": ["Backtracking"],
    "Design": ["HashMap", "Linked List"],
}


def _solved_map(db: Session, user_id: int) -> dict[int, UserQuestion]:
    rows = db.scalars(
        select(UserQuestion).where(UserQuestion.user_id == user_id, UserQuestion.status == "solved")
    )
    return {uq.question_id: uq for uq in rows}


def topic_mastery(db: Session, user_id: int) -> list[dict]:
    solved = _solved_map(db, user_id)
    stages = dict(
        db.execute(
            select(RevisionItem.question_id, RevisionItem.stage).where(RevisionItem.user_id == user_id)
        ).all()
    )
    by_tag: dict[int, list[Question]] = defaultdict(list)
    for tag_id, question in db.execute(
        select(question_tags.c.tag_id, Question)
        .select_from(question_tags)
        .join(Question, Question.id == question_tags.c.question_id)
    ).all():
        by_tag[tag_id].append(question)

    result = []
    for tag in db.scalars(select(Tag).where(Tag.kind == "topic")):
        questions = by_tag.get(tag.id, [])
        score, count = 0.0, 0
        for q in questions:
            uq = solved.get(q.id)
            if uq is None:
                continue
            count += 1
            confidence = uq.confidence or 3
            score += DIFF_WEIGHT.get(q.difficulty, 1.0) * (0.5 + 0.1 * confidence) * (1 + 0.1 * stages.get(q.id, 0))
        result.append(
            {
                "topic": tag.name,
                "solved": count,
                "total": len(questions),
                "mastery": min(100, round(score / MASTERY_TARGET * 100)),
            }
        )
    return sorted(result, key=lambda m: -m["mastery"])


def knowledge_graph(db: Session, user_id: int) -> dict:
    nodes = topic_mastery(db, user_id)
    by_name = {n["topic"]: n for n in nodes}
    edges = [
        {"from": pre, "to": topic}
        for topic, pres in PREREQS.items()
        if topic in by_name
        for pre in pres
        if pre in by_name
    ]
    for node in nodes:
        pres = [by_name[p]["mastery"] for p in PREREQS.get(node["topic"], []) if p in by_name]
        node["prerequisites"] = [p for p in PREREQS.get(node["topic"], []) if p in by_name]
        node["unlocked"] = all(m >= 40 for m in pres)
        node["recommended"] = node["unlocked"] and node["mastery"] < 40
    return {"nodes": nodes, "edges": edges}


def company_readiness(db: Session, user_id: int) -> list[dict]:
    mastery = {m["topic"]: m["mastery"] for m in topic_mastery(db, user_id)}
    solved = _solved_map(db, user_id)

    grouped: dict[str, list[tuple[int, Question]]] = defaultdict(list)
    for name, freq, q in db.execute(
        select(Company.name, QuestionCompany.frequency, Question)
        .select_from(Company)
        .join(QuestionCompany, QuestionCompany.company_id == Company.id)
        .join(Question, Question.id == QuestionCompany.question_id)
    ).all():
        grouped[name].append((freq, q))

    result = []
    for name, items in sorted(grouped.items()):
        total_f = sum(f for f, _ in items) or 1
        solved_f = sum(f for f, q in items if q.id in solved)
        topics = {t.name for _, q in items for t in q.tags if t.kind == "topic"}
        avg_mastery = mean(mastery.get(t, 0) for t in topics) if topics else 0
        coverage = solved_f / total_f
        todo = sorted((x for x in items if x[1].id not in solved), key=lambda x: -x[0])[:5]
        result.append(
            {
                "company": name,
                "readiness": round(60 * coverage + 0.4 * avg_mastery),
                "coverage": round(coverage * 100),
                "solved": sum(1 for _, q in items if q.id in solved),
                "total": len(items),
                "weak_topics": sorted(topics, key=lambda t: mastery.get(t, 0))[:3],
                "next_questions": [
                    {"id": q.id, "title": q.title, "difficulty": q.difficulty, "url": q.url, "frequency": f}
                    for f, q in todo
                ],
            }
        )
    return sorted(result, key=lambda r: -r["readiness"])
