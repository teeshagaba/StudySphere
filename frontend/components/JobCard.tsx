"use client";

import { post } from "@/lib/api";
import type { Job } from "@/lib/types";
import { LogoChip } from "@/components/ui";

function ago(iso: string | null) {
  if (!iso) return "";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  return days <= 0 ? "today" : days === 1 ? "1 day ago" : days < 30 ? `${days} days ago` : `${Math.floor(days / 30)} mo ago`;
}

/** Opens the original posting in a new tab and records it in the application tracker. */
export async function trackApply(j: Job): Promise<boolean> {
  const res = await post<{ created: boolean }>("/jobs/track", { company: j.company, role: j.title.slice(0, 120), url: j.url });
  return res.created;
}

export function JobRow({ job, applied, onApplied }: { job: Job; applied: boolean; onApplied: (j: Job) => void }) {
  return (
    <div className="list-item">
      <div className="grow" style={{ minWidth: 0 }}>
        <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={job.title}>{job.title}</div>
        <div className="muted small">{job.location}{job.posted_at ? ` · ${ago(job.posted_at)}` : ""}</div>
      </div>
      <a className={`btn small ${applied ? "" : "primary"}`} href={job.url} target="_blank" rel="noopener noreferrer"
        onClick={() => !applied && onApplied(job)}>
        {applied ? "Applied ✓" : "Apply ↗"}
      </a>
    </div>
  );
}

export default function JobCard({ job: j, applied, onApplied }: { job: Job; applied: boolean; onApplied: (j: Job) => void }) {
  return (
    <div className="card hover stack">
      <div className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
        <LogoChip name={j.company} />
        <div className="grow" style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600 }}>{j.title}</div>
          <div className="muted small">{j.company}</div>
        </div>
      </div>
      <div className="row">
        <span className="pill">{j.location}</span>
        <span className="pill pattern">{j.level === "entry" ? "fresher / entry" : j.level}</span>
        {j.india && <span className="pill active">India</span>}
        {j.remote && <span className="pill active">remote</span>}
      </div>
      <div className="row spread" style={{ marginTop: "auto" }}>
        <span className="muted small">{j.source}{j.posted_at ? ` · ${ago(j.posted_at)}` : ""}</span>
        <a className={`btn ${applied ? "" : "primary"}`} href={j.url} target="_blank" rel="noopener noreferrer"
          onClick={() => !applied && onApplied(j)}>
          {applied ? "Applied ✓ · open ↗" : "Apply ↗"}
        </a>
      </div>
    </div>
  );
}
