"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { post, useApi } from "@/lib/api";
import { ProgressBar, Ring, Skeleton } from "@/components/ui";

interface FileDoc { path: string; language: string; content: string; reveal: boolean }
interface Task {
  id: string;
  kind: "text" | "prompt" | "choice" | "order" | "lines";
  prompt: string;
  options?: { id: number; text: string }[];
  items?: { id: number; text: string }[];
  expected?: number;
}
interface Exercise {
  id: string; section: string; title: string; difficulty: string; minutes: number; summary: string; context: string;
  timed: boolean; files: FileDoc[]; clues: { label: string; content: string }[]; tasks: Task[];
  best: number | null; attempts: number;
}
interface TaskResult { id: string; score: number; hit: string[]; missed: string[]; feedback: string; explanation: string }
interface Result { score: number; tasks: TaskResult[]; graded_by: "ai" | "rubric"; best: number; attempts: number }

type Answer = string | number | string[] | number[];
const KIND_HINT: Record<Task["kind"], string> = {
  text: "Write your answer", prompt: "Write your prompt", choice: "Choose one", order: "Arrange in the correct order",
  lines: "Click lines in the code to flag them",
};
const ANNOT = /^(.+):(\d+) — (.*)$/;

function fmt(s: number) {
  const m = Math.floor(Math.abs(s) / 60), r = Math.abs(s) % 60;
  return `${s < 0 ? "-" : ""}${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export default function ExercisePage() {
  const { id } = useParams<{ id: string }>();
  const { data: ex, error } = useApi<Exercise>(`/interview/exercises/${id}`);
  const [file, setFile] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [clues, setClues] = useState<Set<number>>(new Set());
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [flags, setFlags] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const sections = useApi<{ sections: { id: string; exercises: { id: string; title: string }[] }[] }>(result ? "/interview/sections" : null);
  const nextEx = useMemo(() => {
    const list = sections.data?.sections.find((s) => s.id === ex?.section)?.exercises ?? [];
    const i = list.findIndex((e) => e.id === ex?.id);
    return i >= 0 ? list[i + 1] : undefined;
  }, [sections.data, ex]);

  useEffect(() => {
    if (result) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [result]);

  useEffect(() => {
    if (!ex) return;
    const init: Record<string, Answer> = {};
    ex.tasks.forEach((t) => { if (t.kind === "order") init[t.id] = t.items!.map((i) => i.id); });
    setAnswers(init);
  }, [ex]);

  const visibleFiles = useMemo(() => ex?.files.filter((f) => !f.reveal || revealed) ?? [], [ex, revealed]);
  const hasHidden = ex?.files.some((f) => f.reveal) ?? false;
  const linesTask = ex?.tasks.find((t) => t.kind === "lines");

  const annotations = useMemo(() => {
    const out = new Map<string, { kind: "hit" | "miss"; label: string }>();
    const r = result?.tasks.find((t) => t.id === linesTask?.id);
    r?.hit.forEach((h) => { const m = ANNOT.exec(h); if (m) out.set(`${m[1]}:${m[2]}`, { kind: "hit", label: m[3] }); });
    r?.missed.forEach((h) => { const m = ANNOT.exec(h); if (m) out.set(`${m[1]}:${m[2]}`, { kind: "miss", label: m[3] }); });
    return out;
  }, [result, linesTask]);

  if (error) return <p className="error">{error}</p>;
  if (!ex) return <div className="stack"><Skeleton height={80} /><Skeleton height={400} /></div>;

  const current = visibleFiles[Math.min(file, visibleFiles.length - 1)];
  const remaining = ex.minutes * 60 - elapsed;
  const set = (tid: string, v: Answer) => setAnswers((a) => ({ ...a, [tid]: v }));

  const toggleFlag = (key: string) => {
    if (!linesTask || result) return;
    setFlags((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const move = (tid: string, idx: number, dir: -1 | 1) => {
    const list = [...(answers[tid] as number[])];
    const j = idx + dir;
    if (j < 0 || j >= list.length) return;
    [list[idx], list[j]] = [list[j], list[idx]];
    set(tid, list);
  };

  const submit = async () => {
    setBusy(true);
    setSubmitError(null);
    try {
      const payload = { ...answers, ...(linesTask ? { [linesTask.id]: Array.from(flags) } : {}) };
      setResult(await post<Result>(`/interview/exercises/${ex.id}/submit`, { answers: payload, seconds: elapsed }));
      setRevealed(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const retry = () => {
    setResult(null);
    setFlags(new Set());
    setElapsed(0);
    const init: Record<string, Answer> = {};
    ex.tasks.forEach((t) => { if (t.kind === "order") init[t.id] = t.items!.map((i) => i.id); });
    setAnswers(init);
  };

  const resultFor = (tid: string) => result?.tasks.find((r) => r.id === tid);

  return (
    <div className="stack">
      <div className="row spread">
        <div>
          <Link href={`/interview?section=${ex.section}`} className="small">← AI-Era Interview Prep</Link>
          <h1 style={{ marginTop: 4 }}>{ex.title}</h1>
          <div className="row small">
            <span className={`diff ${ex.difficulty}`}>{ex.difficulty}</span>
            <span className="muted">{ex.summary}</span>
          </div>
        </div>
        <div className="row">
          {ex.best !== null && <span className="pill">best {ex.best}% · {ex.attempts} attempt{ex.attempts === 1 ? "" : "s"}</span>}
          <span className={`mono stat ${ex.timed && remaining < 300 && !result ? "Hard" : ""}`} style={{ fontSize: 22 }}>
            {ex.timed ? fmt(remaining) : fmt(elapsed)}
          </span>
        </div>
      </div>

      {result && (
        <div className="card glow row" style={{ flexWrap: "nowrap", gap: 20 }}>
          <Ring value={result.score} size={96} stroke={9} />
          <div className="grow">
            <div className="stat-label">Your score</div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>
              {result.score >= 80 ? "Interview-ready on this one 🎯" : result.score >= 50 ? "Solid — review what you missed below" : "Keep going — study the model answers below"}
            </div>
            <div className="muted small">Graded by {result.graded_by === "ai" ? "AI against the rubric" : "built-in rubric"} · best {result.best}% · time {fmt(elapsed)}</div>
          </div>
          <button onClick={retry}>Try again</button>
          {nextEx && <Link href={`/interview/${nextEx.id}`} className="btn primary">Next: {nextEx.title} →</Link>}
        </div>
      )}

      <div className="card">
        <div className="stat-label" style={{ marginBottom: 6 }}>Scenario</div>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontFamily: ex.context.includes("[") && ex.context.includes("->") ? "var(--mono)" : undefined, fontSize: 13 }}>
          {ex.context}
        </div>
        {ex.clues.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>Investigate</div>
            <div className="row">
              {ex.clues.map((c, i) => (
                <button key={c.label} className={clues.has(i) ? "success" : ""} onClick={() => setClues(new Set(clues).add(i))}>
                  {clues.has(i) ? "✓" : "🔍"} {c.label}
                </button>
              ))}
            </div>
            {ex.clues.map((c, i) => clues.has(i) && (
              <pre key={c.label} className="card mono small" style={{ marginTop: 10, whiteSpace: "pre-wrap", background: "#05070b" }}>
                <span className="muted">{"# "}{c.label}{"\n"}</span>{c.content}
              </pre>
            ))}
          </div>
        )}
      </div>

      <div className="ide">
        {ex.files.length > 0 && (
          <div className="card ide-code" style={{ padding: 0 }}>
            <div className="ide-tabs">
              {visibleFiles.map((f, i) => (
                <button key={f.path} className={i === file ? "active" : ""} onClick={() => setFile(i)}>{f.path}</button>
              ))}
              {hasHidden && !revealed && (
                <button className="primary" style={{ margin: 6 }} onClick={() => { setRevealed(true); setFile(visibleFiles.length); }}>✦ Show AI answer</button>
              )}
            </div>
            {linesTask && (
              <div className="small muted" style={{ padding: "6px 14px", borderBottom: "1px solid var(--border)" }}>
                {result ? "Green = found · Amber = missed (hover for details)" : `Click line numbers to flag issues · ${flags.size} flagged (expected ~${linesTask.expected})`}
              </div>
            )}
            {current && (
              <div className="code-view">
                {current.content.split("\n").map((line, i) => {
                  const key = `${current.path}:${i + 1}`;
                  const ann = annotations.get(key);
                  const flagged = flags.has(key);
                  return (
                    <div key={key} className={`code-row ${flagged ? "flagged" : ""} ${ann ? ann.kind : ""} ${linesTask && !result ? "clickable" : ""}`}
                      title={ann?.label} onClick={() => toggleFlag(key)}>
                      <span className="ln">{flagged ? "⚑" : i + 1}</span>
                      <span className="src">{line || " "}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <div className="stack ide-tasks">
          {ex.tasks.map((t, n) => {
            const r = resultFor(t.id);
            return (
              <div key={t.id} className="card stack">
                <div className="row spread">
                  <div className="stat-label">Task {n + 1} · {KIND_HINT[t.kind]}</div>
                  {r && <span className={`mono ${r.score >= 70 ? "Easy" : r.score >= 40 ? "Medium" : "Hard"}`}>{r.score}%</span>}
                </div>
                <div style={{ fontWeight: 600 }}>{t.prompt}</div>

                {(t.kind === "text" || t.kind === "prompt") && (
                  <textarea rows={t.kind === "prompt" ? 7 : 5} className={t.kind === "prompt" ? "mono" : ""} disabled={!!result}
                    placeholder={t.kind === "prompt" ? "You are a senior … Context: … Goal: … Constraints: … Output format: …" : "Think aloud — explain your reasoning…"}
                    value={(answers[t.id] as string) ?? ""} onChange={(e) => set(t.id, e.target.value)} />
                )}

                {t.kind === "choice" && t.options!.map((o) => (
                  <label key={o.id} className={`option ${answers[t.id] === o.id ? "picked" : ""}`}>
                    <input type="radio" name={t.id} disabled={!!result} checked={answers[t.id] === o.id} onChange={() => set(t.id, o.id)} /> {o.text}
                  </label>
                ))}

                {t.kind === "order" && (answers[t.id] as number[] | undefined)?.map((itemId, idx) => (
                  <div key={itemId} className="option row" style={{ flexWrap: "nowrap" }}>
                    <span className="mono muted">{idx + 1}.</span>
                    <span className="grow">{t.items!.find((x) => x.id === itemId)?.text}</span>
                    {!result && <>
                      <button className="ghost small" onClick={() => move(t.id, idx, -1)}>↑</button>
                      <button className="ghost small" onClick={() => move(t.id, idx, 1)}>↓</button>
                    </>}
                  </div>
                ))}

                {t.kind === "lines" && !result && (
                  <div className="small muted">{flags.size ? Array.from(flags).join(", ") : "No lines flagged yet — click line numbers in the code panel."}</div>
                )}

                {r && (
                  <div className="stack">
                    <ProgressBar value={r.score} />
                    {r.hit.length > 0 && <div className="small">{r.hit.map((h) => <div key={h} className="Easy">✓ {h}</div>)}</div>}
                    {r.missed.length > 0 && <div className="small">{r.missed.map((h) => <div key={h} className="Medium">✗ {h}</div>)}</div>}
                    {r.feedback && <div className="small">{r.feedback}</div>}
                    <div className="msg assistant small" style={{ maxWidth: "100%" }}><b>Model answer: </b>{r.explanation}</div>
                  </div>
                )}
              </div>
            );
          })}

          {!result && (
            <div className="row">
              <button className="primary" disabled={busy} onClick={submit}>{busy ? "Grading…" : "Submit for grading"}</button>
              {submitError && <span className="error">{submitError}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
