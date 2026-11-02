"use client";

import Link from "next/link";
import { useApi } from "@/lib/api";
import { ProgressBar } from "@/components/ui";

interface Node { topic: string; solved: number; total: number; mastery: number; prerequisites: string[]; unlocked: boolean; recommended: boolean }
interface Track { track: string; progress: number }

export default function KnowledgePage() {
  const graph = useApi<{ nodes: Node[]; edges: { from: string; to: string }[] }>("/knowledge-graph");
  const learning = useApi<Track[]>("/learning");

  if (graph.error) return <p className="error">{graph.error}</p>;
  if (!graph.data) return <p className="muted">Loading…</p>;

  const recommended = graph.data.nodes.filter((n) => n.recommended && n.total > 0);

  return (
    <div className="stack">
      <h1>Knowledge Graph</h1>
      <p className="muted">Mastery weighs difficulty, your confidence and how far each problem has progressed through revision — not just solved count.</p>

      {recommended.length > 0 && (
        <div className="card">
          <h2>Recommended next</h2>
          {recommended.map((n) => (
            <Link key={n.topic} href={`/dsa?topic=${encodeURIComponent(n.topic)}`} className="pill active">{n.topic}</Link>
          ))}
        </div>
      )}

      <div className="grid cols-4">
        {graph.data.nodes.map((n) => (
          <div key={n.topic} className="card stack" style={{ opacity: n.unlocked ? 1 : 0.55 }}>
            <div className="row spread"><b>{n.topic}</b><span>{n.mastery}%</span></div>
            <ProgressBar value={n.mastery} />
            <div className="muted small">{n.solved}/{n.total} solved</div>
            {n.prerequisites.length > 0 && (
              <div className="small muted">Builds on: {n.prerequisites.join(", ")}</div>
            )}
            {!n.unlocked && <div className="small">🔒 Strengthen prerequisites first (40%+)</div>}
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Beyond DSA</h2>
        <div className="grid cols-4">
          {learning.data?.map((t) => (
            <div key={t.track} className="stack">
              <div className="row spread small"><span>{t.track} Mastery</span><span>{t.progress}%</span></div>
              <ProgressBar value={t.progress} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
