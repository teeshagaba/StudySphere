"use client";

import { useEffect, useState } from "react";
import { patch, useApi } from "@/lib/api";
import type { Contest } from "@/lib/types";
import { LogoChip, PageHead, Skeleton } from "@/components/ui";

interface Stats {
  codeforces: { rating: number | null; max_rating: number | null; contests: number } | null;
  leetcode: { attendedContestsCount: number; rating: number; globalRanking: number; topPercentage: number } | null;
}

function countdown(start: string, now: number) {
  const ms = new Date(start).getTime() - now;
  if (ms <= 0) return null;
  const d = Math.floor(ms / 86_400_000), h = Math.floor((ms / 3_600_000) % 24), m = Math.floor((ms / 60_000) % 60), s = Math.floor((ms / 1000) % 60);
  return d ? `${d}d ${h}h ${m}m` : `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const duration = (min: number) => (min >= 1440 ? `${Math.round(min / 1440)}d` : `${Math.floor(min / 60)}h${min % 60 ? ` ${min % 60}m` : ""}`);

function calendarLink(c: Contest) {
  const fmt = (d: Date) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const start = new Date(c.start);
  const end = new Date(start.getTime() + c.duration_min * 60_000);
  const p = new URLSearchParams({ action: "TEMPLATE", text: c.name, dates: `${fmt(start)}/${fmt(end)}`, details: c.url });
  return `https://calendar.google.com/calendar/render?${p}`;
}

export default function ContestsPage() {
  const contests = useApi<Contest[]>("/contests");
  const stats = useApi<Stats>("/contests/stats");
  const [platform, setPlatform] = useState("");
  const [now, setNow] = useState(Date.now());
  const [handles, setHandles] = useState({ codeforces_handle: "", leetcode_handle: "" });

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const platforms = Array.from(new Set(contests.data?.map((c) => c.platform) ?? [])).sort();
  const list = (contests.data ?? []).filter((c) => !platform || c.platform === platform);
  const live = list.filter((c) => new Date(c.start).getTime() <= now);
  const upcoming = list.filter((c) => new Date(c.start).getTime() > now);

  const saveHandles = async () => {
    const body = Object.fromEntries(Object.entries(handles).filter(([, v]) => v.trim()));
    await patch("/auth/me", body);
    stats.reload();
  };

  const card = (c: Contest) => {
    const cd = countdown(c.start, now);
    return (
      <div key={`${c.platform}-${c.url}-${c.start}`} className="card hover stack">
        <div className="row" style={{ flexWrap: "nowrap" }}>
          <LogoChip name={c.platform} size={34} />
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="muted small">{c.platform}</div>
            <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.name}>{c.name}</div>
          </div>
        </div>
        <div className="row spread small">
          <span className="muted">{new Date(c.start).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
          <span className="mono muted">{duration(c.duration_min)}</span>
        </div>
        <div className="row spread">
          {cd ? <span className="mono" style={{ color: "var(--accent-3)", fontSize: 16 }}>{cd}</span>
              : <span className="pill live"><span className="dot-live" /> LIVE NOW</span>}
          <div className="row">
            <a className="btn ghost small" href={calendarLink(c)} target="_blank" rel="noopener noreferrer">+ Calendar</a>
            <a className="btn primary small" href={c.url} target="_blank" rel="noopener noreferrer">{cd ? "Register" : "Join"} ↗</a>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="stack">
      <PageHead title="Contests" subtitle="Live and upcoming contests from Codeforces, LeetCode, CodeChef, AtCoder and more." />

      <div className="grid cols-2">
        <div className="card">
          <h2>Your ratings</h2>
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <div className="card" style={{ flex: 1 }}>
              <div className="stat-label">Codeforces</div>
              <div className="stat">{stats.data?.codeforces?.rating ?? "—"}</div>
              <div className="muted small">max {stats.data?.codeforces?.max_rating ?? "—"} · {stats.data?.codeforces?.contests ?? 0} contests</div>
            </div>
            <div className="card" style={{ flex: 1 }}>
              <div className="stat-label">LeetCode</div>
              <div className="stat">{stats.data?.leetcode ? Math.round(stats.data.leetcode.rating) : "—"}</div>
              <div className="muted small">{stats.data?.leetcode ? `top ${stats.data.leetcode.topPercentage}% · ${stats.data.leetcode.attendedContestsCount} contests` : "link your handle"}</div>
            </div>
          </div>
        </div>
        <div className="card stack">
          <h2>Link handles</h2>
          <input placeholder="Codeforces handle" value={handles.codeforces_handle} onChange={(e) => setHandles({ ...handles, codeforces_handle: e.target.value })} />
          <input placeholder="LeetCode username" value={handles.leetcode_handle} onChange={(e) => setHandles({ ...handles, leetcode_handle: e.target.value })} />
          <button className="primary" onClick={saveHandles}>Save</button>
        </div>
      </div>

      <div className="row">
        <span className={`pill clickable ${platform === "" ? "active" : ""}`} onClick={() => setPlatform("")}>All · {contests.data?.length ?? 0}</span>
        {platforms.map((p) => (
          <span key={p} className={`pill clickable ${platform === p ? "active" : ""}`} onClick={() => setPlatform(p)}>{p}</span>
        ))}
      </div>

      {contests.error && <p className="error">{contests.error}</p>}
      {!contests.data && !contests.error && <div className="grid cols-3"><Skeleton height={150} count={6} /></div>}

      {live.length > 0 && (
        <>
          <h3><span className="dot-live" /> Live now</h3>
          <div className="grid cols-3 stagger">{live.map(card)}</div>
        </>
      )}
      {upcoming.length > 0 && (
        <>
          <h3>Upcoming</h3>
          <div className="grid cols-3 stagger">{upcoming.map(card)}</div>
        </>
      )}
      {contests.data && list.length === 0 && <div className="empty">no contests found</div>}
    </div>
  );
}
