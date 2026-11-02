"use client";

import { Fragment, Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { post, qs, useApi } from "@/lib/api";
import type { Question, SheetSummary, Status } from "@/lib/types";
import Toast, { PageHead, ProgressBar, Ring, Skeleton } from "@/components/ui";

interface Filters { topics: string[]; patterns: string[]; companies: string[] }
interface ProgressResult { question: Question; synced_sheets: string[]; xp_gained: number; new_badges: string[] }
interface SheetDetail { slug: string; name: string; description: string; questions: Question[] }

export default function Page() {
  return <Suspense><DsaTracker /></Suspense>;
}

type Kind = SheetSummary["kind"];
const KIND_LABEL: Record<Kind, string> = { curated: "Famous sheets", company: "Company-wise", custom: "My imports" };

function DsaTracker() {
  const params = useSearchParams();
  const [sheet, setSheet] = useState(params.get("sheet") ?? "");
  const [kind, setKind] = useState<Kind>(params.get("sheet")?.startsWith("company-") ? "company" : "curated");
  const [f, setF] = useState({
    topic: params.get("topic") ?? "",
    pattern: "",
    company: params.get("company") ?? "",
    difficulty: "",
    status: "",
    q: "",
  });
  const [toast, setToast] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [hintFor, setHintFor] = useState<Question | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [hintBusy, setHintBusy] = useState(false);

  const nextHint = async (q: Question, level: number) => {
    setHintBusy(true);
    try {
      const res = await post<{ hint: string }>("/mentor/hint", { question_id: q.id, level });
      setHints((h) => [...h, res.hint]);
    } catch (e) {
      setToast((e as Error).message);
    } finally {
      setHintBusy(false);
    }
  };
  const openHint = (q: Question) => {
    setHintFor(q);
    setHints([]);
    nextHint(q, 1);
  };
  const revise = async (q: Question) => {
    try {
      await post(`/revision/add/${q.id}`);
      setToast(`"${q.title}" added to today's revision`);
    } catch (e) {
      setToast((e as Error).message);
    }
  };

  const sheets = useApi<SheetSummary[]>("/dsa/sheets");
  const filters = useApi<Filters>("/dsa/filters");
  const all = useApi<Question[]>(sheet ? null : `/dsa/questions${qs(f)}`);
  const detail = useApi<SheetDetail>(sheet ? `/dsa/sheets/${sheet}` : null);

  const rows = useMemo(() => {
    if (!sheet) return all.data;
    const q = f.q.toLowerCase();
    return detail.data?.questions.filter((x) =>
      (!f.topic || x.topics.includes(f.topic)) &&
      (!f.pattern || x.patterns.includes(f.pattern)) &&
      (!f.company || x.companies.some((c) => c.name === f.company)) &&
      (!f.difficulty || x.difficulty === f.difficulty) &&
      (!f.status || x.status === f.status) &&
      (!q || x.title.toLowerCase().includes(q)),
    ) ?? null;
  }, [sheet, all.data, detail.data, f]);

  const current = sheets.data?.find((s) => s.slug === sheet);
  const counts = (k: Kind) => sheets.data?.filter((s) => s.kind === k).length ?? 0;

  const replace = (q: Question) => {
    const swap = (list: Question[]) => list.map((x) => (x.id === q.id ? { ...q, section: x.section } : x));
    if (sheet) detail.setData((d) => (d ? { ...d, questions: swap(d.questions) } : d));
    else all.setData((prev) => (prev ? swap(prev) : prev));
  };

  const setStatus = async (q: Question, status: Status) => {
    let confidence: number | undefined;
    if (status === "solved") {
      const c = window.prompt("Confidence 1-5 (how well could you redo it?)", "3");
      if (c === null) return;
      confidence = Math.min(5, Math.max(1, Number(c) || 3));
    }
    try {
      const res = await post<ProgressResult>(`/dsa/questions/${q.id}/progress`, { status, confidence });
      replace(res.question);
      sheets.reload();
      if (status === "solved") {
        setToast(
          `✓ Marked solved in ${res.synced_sheets.length} sheets · first revision scheduled for tomorrow` +
            (res.new_badges.length ? ` · New badge: ${res.new_badges.join(", ")}` : ""),
        );
      }
    } catch (e) {
      setToast((e as Error).message);
    }
  };

  const select = (key: keyof typeof f, options: string[], label: string) => (
    <select value={f[key]} onChange={(e) => setF({ ...f, [key]: e.target.value })}>
      <option value="">{label}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );

  const loading = sheet ? !detail.data && !detail.error : !all.data && !all.error;
  const error = sheet ? detail.error : all.error;
  let lastSection: string | null = null;

  return (
    <div className="stack">
      <PageHead title="DSA Sheets" subtitle="Solve once, progress syncs to every sheet containing that problem.">
        <button onClick={() => setShowImport(!showImport)}>+ Import sheet</button>
      </PageHead>
      {showImport && <ImportSheet onDone={(msg) => { setToast(msg); setShowImport(false); sheets.reload(); }} />}

      <div className="row spread">
        <div className="tabs">
          {(Object.keys(KIND_LABEL) as Kind[]).map((k) => (
            <button key={k} className={kind === k ? "active" : ""} onClick={() => setKind(k)}>
              {KIND_LABEL[k]}<span className="count">{counts(k)}</span>
            </button>
          ))}
        </div>
        {sheet && <button className="ghost" onClick={() => setSheet("")}>× Clear sheet · show all problems</button>}
      </div>

      <div className="grid cols-4 stagger" key={kind}>
        {!sheets.data && <Skeleton height={110} count={8} />}
        {sheets.data?.filter((s) => s.kind === kind)
          .sort((a, b) => Number(!a.slug.startsWith("striver")) - Number(!b.slug.startsWith("striver")))
          .map((s) => {
          const pct = s.total ? (s.solved / s.total) * 100 : 0;
          return (
            <div
              key={s.slug}
              className={`card clickable row ${sheet === s.slug ? "selected" : ""}`}
              style={{ flexWrap: "nowrap", gap: 14 }}
              onClick={() => setSheet(sheet === s.slug ? "" : s.slug)}
            >
              <Ring value={pct} size={58} stroke={6} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600 }}>{s.name}</div>
                <div className="muted small mono">{s.solved}/{s.total} solved</div>
              </div>
            </div>
          );
        })}
        {sheets.data && counts(kind) === 0 && <div className="empty">nothing here yet — import a sheet</div>}
      </div>

      {current && (
        <div className="card glow">
          <div className="row spread">
            <div>
              <h2 style={{ margin: 0 }}>{current.name}</h2>
              <div className="muted small">{current.description}</div>
            </div>
            <div className="mono stat">{Math.round(current.total ? (current.solved / current.total) * 100 : 0)}%</div>
          </div>
          <div style={{ marginTop: 10 }}><ProgressBar value={current.total ? (current.solved / current.total) * 100 : 0} /></div>
        </div>
      )}

      <div className="card row">
        <input className="search" placeholder="Search problems…" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        {select("topic", filters.data?.topics ?? [], "All topics")}
        {select("pattern", filters.data?.patterns ?? [], "All patterns")}
        {select("company", filters.data?.companies ?? [], "All companies")}
        {select("difficulty", ["Easy", "Medium", "Hard"], "Any difficulty")}
        {select("status", ["todo", "attempted", "solved"], "Any status")}
      </div>

      <div className="card" style={{ padding: 6 }}>
        {error && <p className="error">{error}</p>}
        {loading && <div style={{ padding: 12 }} className="stack"><Skeleton height={40} count={6} /></div>}
        {rows && (
          <table>
            <thead>
              <tr><th style={{ width: 44 }} /><th>Problem</th><th>Patterns</th><th>Companies</th><th>Sheets</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((q) => {
                const header = sheet && q.section && q.section !== lastSection;
                if (sheet) lastSection = q.section;
                return (
                  <Fragment key={q.id}>
                    {header && (
                      <tr className="section-row"><td colSpan={6}>{"// "}{q.section}</td></tr>
                    )}
                    <tr className={q.status === "solved" ? "solved" : ""}>
                      <td>
                        <button
                          className={`check ${q.status === "solved" ? "on" : q.status === "attempted" ? "half" : ""}`}
                          title={q.status === "solved" ? "Mark as todo" : "Mark solved"}
                          onClick={() => setStatus(q, q.status === "solved" ? "todo" : "solved")}
                        >
                          {q.status === "solved" ? "✓" : q.status === "attempted" ? "•" : ""}
                        </button>
                      </td>
                      <td>
                        <a href={q.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text)", fontWeight: 500 }}>{q.title}</a>
                        <div className="row" style={{ marginTop: 4, gap: 6 }}>
                          <span className={`diff ${q.difficulty}`}>{q.difficulty}</span>
                          <span className="muted small">{q.topics.join(" · ")}</span>
                        </div>
                      </td>
                      <td>{q.patterns.map((p) => <span key={p} className="pill pattern">{p}</span>)}</td>
                      <td className="small">
                        {q.companies.slice(0, 3).map((c) => <span key={c.name} className="pill">{c.name}</span>)}
                        {q.companies.length > 3 && <span className="muted small">+{q.companies.length - 3}</span>}
                      </td>
                      <td><span className="pill" title={q.sheets.join("\n")}>{q.sheets.length} sheets</span></td>
                      <td>
                        <div className="row" style={{ flexWrap: "nowrap" }}>
                          <button className="ghost small" title="Get a hint (AI)" onClick={() => openHint(q)}>💡 Hint</button>
                          <button className="ghost small" title="Revise this today" onClick={() => revise(q)}>↻</button>
                          {q.status === "todo" && <button className="ghost small" onClick={() => setStatus(q, "attempted")}>Attempted</button>}
                        </div>
                      </td>
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
        {rows?.length === 0 && <div className="empty">no problems match these filters</div>}
      </div>
      {hintFor && (
        <aside className="drawer">
          <div className="row spread">
            <div className="stat-label">💡 AI hints</div>
            <button className="ghost" onClick={() => setHintFor(null)}>✕</button>
          </div>
          <h2 style={{ margin: "8px 0 2px" }}>{hintFor.title}</h2>
          <div className="row"><span className={`diff ${hintFor.difficulty}`}>{hintFor.difficulty}</span>
            <a href={hintFor.url} target="_blank" rel="noopener noreferrer" className="small">Open problem ↗</a></div>
          <div className="stack" style={{ marginTop: 14 }}>
            {hints.map((h, i) => (
              <div key={i} className="msg assistant" style={{ maxWidth: "100%" }}>
                <div className="stat-label" style={{ marginBottom: 4 }}>{["Nudge", "Pattern", "Steps"][i]}</div>{h}
              </div>
            ))}
            {hintBusy && <div className="skeleton" style={{ height: 60 }} />}
          </div>
          <div className="row" style={{ marginTop: 14 }}>
            {hints.length < 3 && !hintBusy && (
              <button className="primary" onClick={() => nextHint(hintFor, hints.length + 1)}>Next hint ({hints.length + 1}/3)</button>
            )}
            <a className="btn" href={`/mentor?q=${hintFor.id}`}>Ask the mentor →</a>
          </div>
        </aside>
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}

const SAMPLE = `{
  "name": "My GFG Sheet",
  "questions": [
    { "title": "Two Sum", "url": "https://leetcode.com/problems/two-sum/", "difficulty": "Easy", "topics": ["Arrays"] },
    { "title": "Kadane's Algorithm", "difficulty": "Medium", "url": "https://www.geeksforgeeks.org/problems/kadanes-algorithm-1587115620/1", "topics": ["Arrays", "Dynamic Programming"], "companies": {"Microsoft": 3} }
  ]
}`;

function ImportSheet({ onDone }: { onDone: (msg: string) => void }) {
  const [text, setText] = useState(SAMPLE);
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    try {
      const res = await post<{ imported: number; already_solved: number }>("/dsa/sheets/import", JSON.parse(text));
      onDone(`Imported ${res.imported} questions — ${res.already_solved} already solved via other sheets.`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div className="card stack">
      <p className="muted small">Paste any sheet as JSON. Problems are matched to the canonical catalog by LeetCode slug, known URL aliases or title, so existing progress carries over automatically.</p>
      <textarea rows={10} value={text} onChange={(e) => setText(e.target.value)} className="mono" />
      {error && <div className="error">{error}</div>}
      <button className="primary" onClick={submit}>Import</button>
    </div>
  );
}
