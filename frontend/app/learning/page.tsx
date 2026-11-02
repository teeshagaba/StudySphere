"use client";

import Link from "next/link";
import { useState } from "react";
import { put, useApi } from "@/lib/api";
import Toast, { PageHead, ProgressBar, Skeleton } from "@/components/ui";

type LStatus = "not_started" | "learning" | "done";
interface Topic { name: string; status: LStatus; points: string[]; practice: string }
interface Track { track: string; progress: number; topics: Topic[]; resources: { title: string; url: string }[] }

const LABEL: Record<LStatus, string> = { not_started: "Not started", learning: "Learning", done: "Done" };
const MARK: Record<LStatus, string> = { not_started: "○", learning: "◐", done: "●" };

const youtube = (q: string) => `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`;

export default function LearningPage() {
  const { data, error, reload } = useApi<Track[]>("/learning");
  const [active, setActive] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const setStatus = async (track: string, topic: string, status: LStatus) => {
    const res = await put<{ xp_gained: number }>("/learning", { track, topic, status });
    if (res.xp_gained) setToast(`Completed ${topic} ✔`);
    reload();
  };

  if (error) return <p className="error">{error}</p>;
  if (!data) return <div className="stack"><Skeleton height={120} count={3} /></div>;

  const track = data.find((t) => t.track === (active ?? data[0].track)) ?? data[0];

  return (
    <div className="stack">
      <PageHead title="Learn" subtitle="Pick a track, open a topic, read the key ideas, do the hands-on task, then mark it done." />

      <div className="tabs">
        {data.map((t) => (
          <button key={t.track} className={t.track === track.track ? "active" : ""} onClick={() => { setActive(t.track); setOpen(null); }}>
            {t.track}<span className="count">{t.progress}%</span>
          </button>
        ))}
      </div>

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)", alignItems: "start" }}>
        <div className="card stack">
          <div className="row spread"><h2 style={{ margin: 0 }}>{track.track}</h2><span className="mono">{track.progress}%</span></div>
          <ProgressBar value={track.progress} />
          {track.topics.map((topic, i) => {
            const isOpen = open === topic.name;
            return (
              <div key={topic.name} className="list-item" style={{ display: "block" }}>
                <button className="ghost" style={{ width: "100%", textAlign: "left", display: "flex", gap: 10, alignItems: "center", border: "none" }}
                  onClick={() => setOpen(isOpen ? null : topic.name)} aria-expanded={isOpen}>
                  <span className="mono" style={{ color: topic.status === "done" ? "var(--accent-2)" : topic.status === "learning" ? "var(--medium)" : "var(--muted)" }}>
                    {MARK[topic.status]}
                  </span>
                  <span className="grow"><span className="muted mono small">{String(i + 1).padStart(2, "0")}</span> {topic.name}</span>
                  <span className="muted small">{LABEL[topic.status]}</span>
                  <span>{isOpen ? "▾" : "▸"}</span>
                </button>
                {isOpen && (
                  <div className="stack" style={{ padding: "8px 4px 4px 28px" }}>
                    {topic.points.length > 0 && (
                      <div>
                        <div className="stat-label">Key ideas</div>
                        <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.6 }}>
                          {topic.points.map((p) => <li key={p}>{p}</li>)}
                        </ul>
                      </div>
                    )}
                    {topic.practice && (
                      <div className="card" style={{ padding: 12 }}>
                        <div className="stat-label">Hands-on task</div>
                        <div style={{ marginTop: 4 }}>{topic.practice}</div>
                      </div>
                    )}
                    <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                      <a className="btn" href={youtube(`${topic.name} ${track.track} tutorial`)} target="_blank" rel="noopener noreferrer">▶ Watch videos</a>
                      <Link className="btn" href={`/mentor?mode=teacher&topic=${encodeURIComponent(`${topic.name} (${track.track})`)}`}>✦ Ask the mentor to teach it</Link>
                    </div>
                    <div className="row" style={{ gap: 8 }}>
                      <span className="small muted">Mark as:</span>
                      {(["not_started", "learning", "done"] as LStatus[]).map((s) => (
                        <button key={s} className={topic.status === s ? (s === "done" ? "success" : "primary") : ""}
                          onClick={() => setStatus(track.track, topic.name, s)}>{LABEL[s]}</button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="card stack">
          <h2 style={{ margin: 0 }}>Free courses &amp; books</h2>
          <div className="muted small">Hand-picked, free resources for {track.track}. Use them alongside the topic lessons.</div>
          {track.resources.map((r) => (
            <a key={r.url} href={r.url} target="_blank" rel="noopener noreferrer" className="list-item" style={{ color: "inherit" }}>
              <span className="grow">{r.title}</span><span>↗</span>
            </a>
          ))}
        </div>
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
