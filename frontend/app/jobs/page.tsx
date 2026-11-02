"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { qs, useApi } from "@/lib/api";
import { jobSearchLinks } from "@/lib/links";
import type { CompanyProfile, Job, JobsResponse } from "@/lib/types";
import JobCard, { trackApply } from "@/components/JobCard";
import Toast, { LogoChip, PageHead, Skeleton } from "@/components/ui";

export default function Page() {
  return <Suspense><JobsBoard /></Suspense>;
}

const PRESETS = {
  "india-fresher": { label: "India · Fresher", india: "true", fresher: "true", level: "", remote: "" },
  "india-all": { label: "India · All levels", india: "true", fresher: "", level: "", remote: "" },
  internships: { label: "Internships", india: "", fresher: "", level: "intern", remote: "" },
  remote: { label: "Remote", india: "", fresher: "", level: "", remote: "true" },
  all: { label: "Worldwide", india: "", fresher: "", level: "", remote: "" },
} as const;
type Preset = keyof typeof PRESETS;

function JobsBoard() {
  const params = useSearchParams();
  const company = params.get("company") ?? "";
  const [preset, setPreset] = useState<Preset>(company ? "all" : "india-fresher");
  const [f, setF] = useState({ q: "", company });
  const [toast, setToast] = useState<string | null>(null);
  const p = PRESETS[preset];
  const jobs = useApi<JobsResponse>(`/jobs${qs({ ...f, india: p.india, fresher: p.fresher, level: p.level, remote: p.remote })}`);
  const directory = useApi<CompanyProfile[]>("/jobs/companies");
  const tracked = useApi<string[]>("/jobs/tracked");
  const trackedSet = new Set(tracked.data ?? []);

  const apply = async (j: Job) => {
    try {
      const created = await trackApply(j);
      tracked.setData((prev) => [...(prev ?? []), j.url]);
      if (created) setToast(`Tracked "${j.title}" at ${j.company} in Applications.`);
    } catch (e) {
      setToast((e as Error).message);
    }
  };

  const profile = directory.data?.find((c) => c.name.toLowerCase() === f.company.toLowerCase());
  const links = jobSearchLinks(f.company, { india: !!p.india, fresher: !!p.fresher || p.level === "intern" });

  return (
    <div className="stack">
      <PageHead title="Jobs Board" subtitle="Live openings pulled from company career sites. Apply opens the original posting and auto-tracks it in Applications." />

      <div className="tabs">
        {(Object.keys(PRESETS) as Preset[]).map((k) => (
          <button key={k} className={preset === k ? "active" : ""} onClick={() => setPreset(k)}>{PRESETS[k].label}</button>
        ))}
      </div>

      <div className="card row">
        <input className="search" placeholder="Search role, company, city, skill…" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <input list="companies" placeholder="Any company…" value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })} />
        <datalist id="companies">{directory.data?.map((c) => <option key={c.name} value={c.name} />)}</datalist>
        {f.company && <button className="ghost" onClick={() => setF({ ...f, company: "" })}>× clear</button>}
      </div>

      {f.company && (
        <div className="card glow row" style={{ flexWrap: "nowrap", gap: 14 }}>
          <LogoChip name={f.company} size={44} />
          <div className="grow">
            <h2 style={{ margin: 0 }}>{profile?.name ?? f.company}</h2>
            <div className="muted small">{profile?.roles.length ? `Hires for: ${profile.roles.join(" · ")}` : "Search this company on every job site"}</div>
          </div>
          {profile && <a className="btn primary" href={profile.careers} target="_blank" rel="noopener noreferrer">Official careers ↗</a>}
        </div>
      )}

      <div className="card">
        <div className="stat-label" style={{ marginBottom: 8 }}>Search {f.company || "all companies"} on job sites{p.india ? " · India" : ""}{p.fresher ? " · fresher" : ""}</div>
        <div className="row">
          {links.map(([name, url]) => <a key={name} className="btn" href={url} target="_blank" rel="noopener noreferrer">{name} ↗</a>)}
        </div>
      </div>

      {jobs.error && <p className="error">{jobs.error}</p>}
      {!jobs.data && !jobs.error && <div className="grid cols-3"><Skeleton height={150} count={9} /></div>}
      {jobs.data && <div className="muted small mono">{jobs.data.total} openings from company career sites</div>}

      <div className="grid cols-3 stagger" key={`${preset}${f.company}`}>
        {jobs.data?.items.map((j) => <JobCard key={j.id} job={j} applied={trackedSet.has(j.url)} onApplied={apply} />)}
      </div>
      {jobs.data?.items.length === 0 && (
        <div className="empty">no direct listings in our feeds for this filter right now — use the job-site buttons above, they open pre-filtered searches</div>
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
