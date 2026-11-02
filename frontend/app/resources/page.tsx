"use client";

import { useState } from "react";
import { del, post, useApi } from "@/lib/api";
import type { Resource } from "@/lib/types";
import Toast, { PageHead, Skeleton } from "@/components/ui";

const KIND_LABEL: Record<Resource["kind"], string> = {
  book: "Free books", notes: "Notes & guides", cheatsheet: "Cheat sheets", practice: "Practice", course: "Courses", video: "Video channels",
};
const KIND_ICON: Record<Resource["kind"], string> = { book: "▤", notes: "✎", cheatsheet: "≡", practice: "{}", course: "◎", video: "▶" };

export default function ResourcesPage() {
  const { data, error, setData } = useApi<{ kinds: Resource["kind"][]; items: Resource[] }>("/resources");
  const [kind, setKind] = useState<"" | Resource["kind"] | "mine">("");
  const [tag, setTag] = useState("");
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ title: "", url: "", kind: "notes" as Resource["kind"], tags: "" });
  const [toast, setToast] = useState<string | null>(null);

  const items = (data?.items ?? []).filter((r) =>
    (!kind || (kind === "mine" ? r.mine : r.kind === kind)) &&
    (!tag || r.tags.includes(tag)) &&
    (!q || `${r.title} ${r.author} ${r.description}`.toLowerCase().includes(q.toLowerCase())),
  );
  const tags = Array.from(new Set((data?.items ?? []).flatMap((r) => r.tags))).sort();

  const add = async () => {
    try {
      const r = await post<Resource>("/resources", { ...form, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) });
      setData((d) => (d ? { ...d, items: [r, ...d.items] } : d));
      setForm({ title: "", url: "", kind: "notes", tags: "" });
      setAdding(false);
      setToast("Saved to My resources");
    } catch (e) {
      setToast((e as Error).message);
    }
  };

  const remove = async (r: Resource) => {
    if (r.id === null) return;
    await del(`/resources/${r.id}`);
    setData((d) => (d ? { ...d, items: d.items.filter((x) => !(x.mine && x.id === r.id)) } : d));
  };

  return (
    <div className="stack">
      <PageHead title="Free Resources" subtitle="Legally free books, lecture notes, cheat sheets, practice sets and channels — plus your own notes links.">
        <button className="primary" onClick={() => setAdding(!adding)}>+ Add my notes</button>
      </PageHead>

      {adding && (
        <div className="card stack">
          <div className="muted small">Add a link to your own handwritten/digital notes (Google Drive, Notion, GitHub, PDF…). Only you can see it.</div>
          <div className="row">
            <input className="grow" placeholder="Title (e.g. My DP handwritten notes)" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input className="grow" placeholder="https://…" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Resource["kind"] })}>
              {data?.kinds.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
            </select>
            <input placeholder="tags, comma separated" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
            <button className="primary" onClick={add} disabled={!form.title || !form.url}>Save</button>
          </div>
        </div>
      )}

      <div className="row spread">
        <div className="tabs">
          <button className={kind === "" ? "active" : ""} onClick={() => setKind("")}>All<span className="count">{data?.items.length ?? 0}</span></button>
          {data?.kinds.map((k) => (
            <button key={k} className={kind === k ? "active" : ""} onClick={() => setKind(k)}>
              {KIND_ICON[k]} {KIND_LABEL[k]}
            </button>
          ))}
          <button className={kind === "mine" ? "active" : ""} onClick={() => setKind("mine")}>★ Mine</button>
        </div>
        <input className="search" style={{ maxWidth: 320 }} placeholder="Search resources…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="row">
        <span className={`pill clickable ${tag === "" ? "active" : ""}`} onClick={() => setTag("")}>all topics</span>
        {tags.map((t) => <span key={t} className={`pill clickable ${tag === t ? "active" : ""}`} onClick={() => setTag(tag === t ? "" : t)}>{t}</span>)}
      </div>

      {error && <p className="error">{error}</p>}
      {!data && !error && <div className="grid cols-3"><Skeleton height={140} count={9} /></div>}

      <div className="grid cols-3 stagger" key={`${kind}${tag}`}>
        {items.map((r) => (
          <div key={`${r.mine ? "m" : "c"}${r.id ?? r.url}`} className={`card hover stack ${r.mine ? "glow" : ""}`}>
            <div className="row spread" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
              <div>
                <div className="stat-label">{KIND_ICON[r.kind]} {KIND_LABEL[r.kind]}</div>
                <div style={{ fontWeight: 600, fontSize: 15, marginTop: 4 }}>{r.title}</div>
                <div className="muted small">{r.author}</div>
              </div>
              <span className="pill active">FREE</span>
            </div>
            {r.description && <div className="small" style={{ color: "#b6c0cf" }}>{r.description}</div>}
            <div>{r.tags.map((t) => <span key={t} className="pill">{t}</span>)}</div>
            <div className="row spread" style={{ marginTop: "auto" }}>
              <span className="muted small mono">{new URL(r.url).hostname.replace(/^www\./, "")}</span>
              <div className="row">
                {r.mine && <button className="danger small" onClick={() => remove(r)}>Delete</button>}
                <a className="btn primary" href={r.url} target="_blank" rel="noopener noreferrer">Open ↗</a>
              </div>
            </div>
          </div>
        ))}
      </div>
      {data && items.length === 0 && <div className="empty">nothing here yet</div>}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
