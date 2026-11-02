"use client";

import Link from "next/link";
import { useState } from "react";
import { post, useApi } from "@/lib/api";
import type { Difficulty, RevisionItem } from "@/lib/types";
import Toast, { PageHead, Skeleton } from "@/components/ui";

interface Overview {
  intervals: number[];
  due: RevisionItem[];
  upcoming: RevisionItem[];
  attempted: { id: number; title: string; difficulty: Difficulty; url: string }[];
  total_tracked: number;
}

export default function RevisionPage() {
  const { data, error, reload } = useApi<Overview>("/revision?days=60");
  const [toast, setToast] = useState<string | null>(null);

  const review = async (item: RevisionItem, recalled: boolean) => {
    const res = await post<{ item: RevisionItem }>(`/revision/${item.id}/review`, { recalled });
    setToast(res.item.completed ? `Mastered "${item.question.title}" 🎯` : recalled ? `Nice! Next review on ${res.item.due_on}` : "No worries — it's back tomorrow.");
    reload();
  };
  const addNow = async (id: number) => {
    await post(`/revision/add/${id}`);
    setToast("Added to today's revision");
    reload();
  };

  if (error) return <p className="error">{error}</p>;
  if (!data) return <div className="stack"><Skeleton height={160} count={2} /></div>;

  const row = (i: RevisionItem, due: boolean) => (
    <div key={i.id} className="list-item">
      <div className="grow">
        <a href={i.question.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text)", fontWeight: 500 }}>{i.question.title}</a>
        <div className="row small" style={{ gap: 8, marginTop: 3 }}>
          <span className={`diff ${i.question.difficulty}`}>{i.question.difficulty}</span>
          <span className="muted">Round {i.stage + 1}/{data.intervals.length}{i.lapses ? ` · forgot ${i.lapses}×` : ""}</span>
          {!due && <span className="muted mono">due {i.due_on}</span>}
        </div>
      </div>
      {due ? (
        <div className="row">
          <button className="success" onClick={() => review(i, true)}>✓ Remembered</button>
          <button className="danger" onClick={() => review(i, false)}>✗ Forgot</button>
        </div>
      ) : (
        <button className="ghost" onClick={() => review(i, true)}>Revise now</button>
      )}
    </div>
  );

  return (
    <div className="stack">
      <PageHead title="Revision" subtitle={`Spaced repetition: every solved problem comes back after ${data.intervals.map((d) => `${d}d`).join(" → ")}. Forget it and it restarts from day 1.`} />

      {data.total_tracked === 0 && data.attempted.length === 0 && (
        <div className="card glow empty" style={{ fontFamily: "inherit" }}>
          <h2 style={{ color: "var(--text)" }}>Your revision queue is empty</h2>
          <p>Mark problems as <b>Solved</b> in DSA Sheets — each one is scheduled here automatically (first review the next day).<br />
            Use the <b>↻</b> button on any problem to add it for revision today.</p>
          <Link href="/dsa" className="btn primary">Go to DSA Sheets</Link>
        </div>
      )}

      <div className="card">
        <div className="row spread"><h2>Due today</h2><span className="pill active">{data.due.length}</span></div>
        {data.due.length === 0 && <div className="muted small">Nothing due today{data.upcoming.length ? " — you can revise upcoming ones early below." : "."}</div>}
        {data.due.map((i) => row(i, true))}
      </div>

      {data.attempted.length > 0 && (
        <div className="card">
          <div className="row spread"><h2>Attempted but not solved</h2><span className="pill">{data.attempted.length}</span></div>
          {data.attempted.map((q) => (
            <div key={q.id} className="list-item">
              <div className="grow">
                <a href={q.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text)" }}>{q.title}</a>{" "}
                <span className={`diff ${q.difficulty}`}>{q.difficulty}</span>
              </div>
              <button className="ghost" onClick={() => addNow(q.id)}>+ Revise today</button>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="row spread"><h2>Coming up (60 days)</h2><span className="pill">{data.upcoming.length}</span></div>
        {data.upcoming.length === 0 && <div className="muted small">Nothing scheduled yet.</div>}
        {data.upcoming.map((i) => row(i, false))}
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
