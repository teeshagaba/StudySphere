"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useApi } from "@/lib/api";
import { PageHead, ProgressBar, Ring, Skeleton } from "@/components/ui";

interface ExerciseSummary { id: string; title: string; difficulty: string; minutes: number; summary: string; best: number | null; attempts: number }
interface Section {
  id: string; title: string; tagline: string; skill: string; progress: number; exercises: ExerciseSummary[];
  guide: { steps: string[]; resources: { title: string; url: string }[] };
}
interface Component { name: string; score: number; href: string }
interface Readiness {
  readiness: number;
  split: { fundamentals: { weight: number; score: number }; engineering: { weight: number; score: number } };
  fundamentals: Component[];
  engineering: Component[];
  skills: Record<string, number>;
  next_steps: Component[];
}

const ICONS: Record<string, string> = {
  comprehension: "⌕", ai_assist: "✦", debugging: "🐞", repos: "⎇", interview: "◷", prompts: "❯", system: "⇄", review: "✓", verify: "⚠",
};
const DIFF_CLASS: Record<string, string> = { Easy: "Easy", Medium: "Medium", Hard: "Hard" };

export default function Page() {
  return <Suspense><InterviewHub /></Suspense>;
}

function InterviewHub() {
  const params = useSearchParams();
  const data = useApi<{ sections: Section[]; ai_grading: boolean }>("/interview/sections");
  const ready = useApi<Readiness>("/interview/readiness");
  const [active, setActive] = useState(params.get("section") ?? "comprehension");
  const section = data.data?.sections.find((s) => s.id === active);

  return (
    <div className="stack">
      <PageHead title="AI-Era Interview Prep" subtitle="Modern interviews test code comprehension, debugging, system understanding and AI collaboration — not just DSA." />

      {!ready.data ? <Skeleton height={220} /> : (
        <div className="grid cols-2">
          <div className="card glow row" style={{ flexWrap: "nowrap", gap: 22 }}>
            <Ring value={ready.data.readiness} size={132} stroke={11} label={`${ready.data.readiness}`} />
            <div className="grow stack">
              <div>
                <div className="stat-label">Industry Readiness Score</div>
                <div className="muted small">30% fundamentals + 70% real engineering</div>
              </div>
              <div>
                <div className="row spread small"><span>Fundamentals <span className="muted">(DSA · OS · DBMS · OOP)</span></span><span className="mono">{ready.data.split.fundamentals.score}%</span></div>
                <ProgressBar value={ready.data.split.fundamentals.score} />
              </div>
              <div>
                <div className="row spread small"><span>Real engineering <span className="muted">(code reading · debugging · AI · systems · dev)</span></span><span className="mono">{ready.data.split.engineering.score}%</span></div>
                <ProgressBar value={ready.data.split.engineering.score} />
              </div>
            </div>
          </div>
          <div className="card">
            <h2>Skill breakdown</h2>
            <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              {Object.entries(ready.data.skills).map(([name, v]) => (
                <div key={name} style={{ textAlign: "center" }}>
                  <div style={{ display: "flex", justifyContent: "center" }}><Ring value={v} size={64} stroke={6} /></div>
                  <div className="small" style={{ marginTop: 4 }}>{name}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {ready.data && (
        <div className="grid cols-2">
          <div className="card">
            <h2>Recommended next</h2>
            {ready.data.next_steps.map((s) => (
              <Link key={s.name} href={s.href} className="list-item" style={{ color: "inherit" }} onClick={() => {
                const sec = new URL(s.href, "http://x").searchParams.get("section");
                if (sec) setActive(sec);
              }}>
                <span className="grow">Improve <b>{s.name}</b></span>
                <span className="mono muted">{s.score}%</span><span>→</span>
              </Link>
            ))}
          </div>
          <div className="card">
            <h2>Learning split</h2>
            <div className="row" style={{ alignItems: "stretch", flexWrap: "nowrap" }}>
              <div className="grow">
                <div className="stat-label">30% Fundamentals</div>
                {ready.data.fundamentals.map((c) => (
                  <Link key={c.name} href={c.href} className="row spread small" style={{ color: "inherit", padding: "3px 0" }}>
                    <span>{c.name}</span><span className="mono muted">{c.score}%</span>
                  </Link>
                ))}
              </div>
              <div className="grow">
                <div className="stat-label">70% Real engineering</div>
                {ready.data.engineering.map((c) => (
                  <Link key={c.name} href={c.href} className="row spread small" style={{ color: "inherit", padding: "3px 0" }}>
                    <span>{c.name}</span><span className="mono muted">{c.score}%</span>
                  </Link>
                ))}
              </div>
            </div>
            <div className="muted small" style={{ marginTop: 8 }}>OS, DBMS, OOP, Git, Docker and Projects are tracked in <Link href="/learning">Learning</Link>.</div>
          </div>
        </div>
      )}

      {data.data && !data.data.ai_grading && (
        <div className="muted small">Grading uses built-in rubrics. Add an AI key in backend/.env for AI-graded feedback on written answers.</div>
      )}

      <div className="tabs">
        {data.data?.sections.map((s) => (
          <button key={s.id} className={active === s.id ? "active" : ""} onClick={() => setActive(s.id)}>
            {ICONS[s.id]} {s.title}<span className="count">{s.progress}%</span>
          </button>
        ))}
      </div>

      {!data.data && <div className="grid cols-3"><Skeleton height={150} count={6} /></div>}
      {section && (
        <>
          <div className="card stack">
            <div className="row spread">
              <h2 style={{ margin: 0 }}>{ICONS[section.id]} {section.title}</h2>
              <span className="muted small mono">
                {section.exercises.filter((e) => e.best !== null).length}/{section.exercises.length} practised
              </span>
            </div>
            <div className="muted">{section.tagline}</div>
            <div className="grid cols-2" style={{ alignItems: "start" }}>
              <div>
                <div className="stat-label">How to approach it</div>
                <ol style={{ margin: "6px 0 0", paddingLeft: 20, lineHeight: 1.6 }}>
                  {section.guide.steps.map((s) => <li key={s}>{s}</li>)}
                </ol>
              </div>
              <div className="stack" style={{ gap: 6 }}>
                <div className="stat-label">Learn more (free)</div>
                {section.guide.resources.map((r) => (
                  <a key={r.url} href={r.url} target="_blank" rel="noopener noreferrer" className="small">{r.title} ↗</a>
                ))}
                {(() => {
                  const next = section.exercises.find((e) => e.best === null) ?? [...section.exercises].sort((a, b) => (a.best ?? 0) - (b.best ?? 0))[0];
                  return next && (
                    <Link href={`/interview/${next.id}`} className="btn primary" style={{ alignSelf: "flex-start", marginTop: 6 }}>
                      {next.best === null ? "Start next exercise" : "Improve weakest exercise"} →
                    </Link>
                  );
                })()}
              </div>
            </div>
          </div>
          <div className="grid cols-3 stagger" key={section.id}>
            {section.exercises.map((e) => (
              <Link key={e.id} href={`/interview/${e.id}`} className="card hover stack" style={{ color: "inherit" }}>
                <div className="row spread">
                  <span className={`diff ${DIFF_CLASS[e.difficulty]}`}>{e.difficulty}</span>
                  <span className="muted small mono">~{e.minutes} min</span>
                </div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{e.title}</div>
                <div className="muted small">{e.summary}</div>
                <div style={{ marginTop: "auto" }}>
                  {e.best === null ? <span className="pill">Not attempted</span> : (
                    <>
                      <div className="row spread small"><span>Best score</span><span className="mono">{e.best}%</span></div>
                      <ProgressBar value={e.best} />
                    </>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
