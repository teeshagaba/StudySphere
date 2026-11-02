"use client";

import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/api";
import { jobSearchLinks } from "@/lib/links";
import type { CompanyProfile, Job, Readiness } from "@/lib/types";
import { JobRow, trackApply } from "@/components/JobCard";
import Toast, { LogoChip, PageHead, ProgressBar, Ring, Skeleton } from "@/components/ui";

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
type Filter = "featured" | "india" | "all";

export default function CompaniesPage() {
  const readiness = useApi<Readiness[]>("/companies/readiness");
  const directory = useApi<CompanyProfile[]>("/jobs/companies");
  const tracked = useApi<string[]>("/jobs/tracked");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("featured");
  const [toast, setToast] = useState<string | null>(null);
  const applied = new Set(tracked.data ?? []);
  const byName = new Map((readiness.data ?? []).map((r) => [r.company, r]));

  const apply = async (j: Job) => {
    try {
      if (await trackApply(j)) setToast(`Tracked "${j.title}" at ${j.company} in Applications.`);
      tracked.setData((prev) => [...(prev ?? []), j.url]);
    } catch (e) { setToast((e as Error).message); }
  };

  const needle = q.trim().toLowerCase();
  const list = (directory.data ?? []).filter((c) =>
    needle ? c.name.toLowerCase().includes(needle) : filter === "featured" ? c.featured : filter === "india" ? c.india_roles > 0 : true,
  );
  const exact = directory.data?.some((c) => c.name.toLowerCase() === needle);

  const links = (name: string) => (
    <div className="row">
      {jobSearchLinks(name, { india: true, fresher: true }).slice(0, 4).map(([site, url]) => (
        <a key={site} className="btn ghost small" href={url} target="_blank" rel="noopener noreferrer">{site} ↗</a>
      ))}
    </div>
  );

  return (
    <div className="stack">
      <PageHead title="Companies" subtitle="Interview process, readiness, company-wise sheets, recent openings and one-click searches on LinkedIn, Naukri & more.">
        <input className="search" placeholder="Search or type any company…" value={q} onChange={(e) => setQ(e.target.value)} />
      </PageHead>

      {!needle && (
        <div className="tabs">
          <button className={filter === "featured" ? "active" : ""} onClick={() => setFilter("featured")}>FAANG / MAANG & top</button>
          <button className={filter === "india" ? "active" : ""} onClick={() => setFilter("india")}>Hiring in India now</button>
          <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>All companies<span className="count">{directory.data?.length ?? 0}</span></button>
        </div>
      )}

      {needle && !exact && (
        <div className="card glow stack">
          <div className="row" style={{ flexWrap: "nowrap", gap: 14 }}>
            <LogoChip name={q} size={44} />
            <div className="grow">
              <h2 style={{ margin: 0 }}>{q}</h2>
              <div className="muted small">Not in our directory yet — search its openings directly:</div>
            </div>
            <a className="btn primary" href={`https://www.google.com/search?q=${encodeURIComponent(q + " careers software engineer")}`} target="_blank" rel="noopener noreferrer">Careers page ↗</a>
          </div>
          {links(q)}
        </div>
      )}

      {!directory.data && <div className="grid cols-3"><Skeleton height={320} count={6} /></div>}

      <div className="grid cols-3 stagger" key={`${filter}${needle}`}>
        {list.map((c) => {
          const r = byName.get(c.name);
          return (
            <div key={c.name} className="card hover stack">
              <div className="row" style={{ flexWrap: "nowrap", gap: 14 }}>
                <LogoChip name={c.name} size={44} />
                <div className="grow" style={{ minWidth: 0 }}>
                  <h2 style={{ margin: 0 }}>{c.name}</h2>
                  <div className="muted small">
                    {c.open_roles ? `${c.open_roles} open roles${c.india_roles ? ` · ${c.india_roles} in India` : ""}` : c.roles.join(" · ") || "Tech roles"}
                  </div>
                </div>
                {r && <Ring value={r.readiness} size={56} stroke={6} />}
              </div>

              {r && (
                <div>
                  <ProgressBar value={r.coverage} />
                  <div className="muted small" style={{ marginTop: 4 }}>Your readiness · {r.solved}/{r.total} tagged questions solved</div>
                </div>
              )}

              {c.process.length > 0 && (
                <details>
                  <summary className="small" style={{ cursor: "pointer" }}>Interview process & focus</summary>
                  <ol className="small" style={{ margin: "8px 0", paddingLeft: 18, lineHeight: 1.7 }}>
                    {c.process.map((s) => <li key={s}>{s}</li>)}
                  </ol>
                  {(r?.weak_topics.length ? r.weak_topics : c.focus).map((t) => (
                    <Link key={t} href={`/dsa?topic=${encodeURIComponent(t)}`} className="pill clickable">{t}</Link>
                  ))}
                </details>
              )}

              <div>
                <h3>Recent openings</h3>
                {c.recent.length === 0 && <div className="muted small">No live listings in our feed — use the buttons below.</div>}
                {c.recent.slice(0, 4).map((j) => <JobRow key={j.id} job={j} applied={applied.has(j.url)} onApplied={apply} />)}
              </div>

              {links(c.name)}

              <div className="row" style={{ marginTop: "auto" }}>
                {r && <Link className="btn" href={`/dsa?sheet=company-${slug(c.name)}`}>Company sheet</Link>}
                {c.open_roles > 0 && <Link className="btn" href={`/jobs?company=${encodeURIComponent(c.name)}`}>All {c.open_roles} jobs</Link>}
                <a className="btn primary" href={c.careers} target="_blank" rel="noopener noreferrer">Careers ↗</a>
              </div>
            </div>
          );
        })}
      </div>
      {directory.data && list.length === 0 && !needle && <div className="empty">no companies for this filter right now</div>}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
