"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { del, post, put, useApi } from "@/lib/api";
import type { Application } from "@/lib/types";
import Toast, { LogoChip, PageHead } from "@/components/ui";

const COLUMNS: { id: Application["status"]; label: string }[] = [
  { id: "applied", label: "Applied" },
  { id: "oa", label: "Online Assessment" },
  { id: "interview", label: "Interview" },
  { id: "offer", label: "Offer" },
  { id: "rejected", label: "Rejected" },
];
const EMPTY = { company: "", role: "", status: "applied" as Application["status"], applied_on: "", next_step_on: "", link: "", notes: "" };

export default function Page() {
  return <Suspense><CareerPage /></Suspense>;
}

function CareerPage() {
  const params = useSearchParams();
  const router = useRouter();
  const { data, error, reload } = useApi<Application[]>("/career");
  const [form, setForm] = useState(EMPTY);
  const [links, setLinks] = useState("");
  const [showManual, setShowManual] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const bookmarklet = useRef<HTMLAnchorElement>(null);
  const handled = useRef(false);

  useEffect(() => {
    // React blocks javascript: URLs in JSX, so the bookmarklet href is set directly.
    const code = `javascript:(()=>{window.open('${window.location.origin}/career?add='+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title),'_blank')})()`;
    bookmarklet.current?.setAttribute("href", code);
  }, []);

  useEffect(() => {
    const url = params.get("add");
    if (!url || handled.current) return;
    handled.current = true;
    post<Application & { created: boolean }>("/career/quick", { url, title: params.get("title") ?? "" })
      .then((a) => { setToast(a.created ? `Tracked ${a.role} at ${a.company}` : `Already tracking ${a.company}`); reload(); })
      .catch((e: Error) => setToast(e.message))
      .finally(() => router.replace("/career"));
  }, [params, reload, router]);

  const payload = (a: typeof EMPTY) => ({ ...a, applied_on: a.applied_on || null, next_step_on: a.next_step_on || null, link: a.link || null });

  const addLinks = async () => {
    const urls = links.split(/\s+/).map((s) => s.trim()).filter((s) => /^https?:\/\//.test(s));
    if (!urls.length) return setToast("Paste at least one job link (https://…)");
    try {
      if (urls.length === 1) {
        const a = await post<Application & { created: boolean }>("/career/quick", { url: urls[0] });
        setToast(a.created ? `Tracked ${a.role} at ${a.company} — edit if needed` : `Already tracking ${a.company}`);
      } else {
        const r = await post<{ created: number; skipped: number }>("/career/bulk", { items: urls.map((url) => ({ url })) });
        setToast(`Tracked ${r.created} applications${r.skipped ? ` (${r.skipped} already tracked)` : ""}`);
      }
      setLinks("");
      reload();
    } catch (e) { setToast((e as Error).message); }
  };

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await post("/career", payload(form));
      setForm(EMPTY);
      reload();
    } catch (err) { setToast((err as Error).message); }
  };

  const move = async (a: Application, status: Application["status"]) => {
    await put(`/career/${a.id}`, payload({ ...a, status, applied_on: a.applied_on ?? "", next_step_on: a.next_step_on ?? "", link: a.link ?? "" }));
    reload();
  };

  const rename = async (a: Application) => {
    const role = window.prompt("Role", a.role);
    if (role === null) return;
    const company = window.prompt("Company", a.company);
    if (company === null) return;
    await put(`/career/${a.id}`, payload({ ...a, role, company, applied_on: a.applied_on ?? "", next_step_on: a.next_step_on ?? "", link: a.link ?? "" }));
    reload();
  };

  const remove = async (a: Application) => {
    if (!confirm(`Remove ${a.company}?`)) return;
    await del(`/career/${a.id}`);
    reload();
  };

  return (
    <div className="stack">
      <PageHead title="Applications" subtitle="Your job pipeline. No typing needed — pick any of the ways below." />

      <div className="grid cols-3 stagger">
        <div className="card stack">
          <div className="stat-label">① Automatic</div>
          <div>Click <b>Apply</b> on the <Link href="/jobs">Jobs Board</Link> or <Link href="/companies">Companies</Link> — the job is tracked here instantly.</div>
        </div>
        <div className="card stack">
          <div className="stat-label">② Paste link(s)</div>
          <textarea rows={3} placeholder={"Paste one or many job URLs (LinkedIn, Naukri, Greenhouse, Workday, careers pages…)"} value={links} onChange={(e) => setLinks(e.target.value)} />
          <button className="primary" onClick={addLinks}>Track</button>
        </div>
        <div className="card stack">
          <div className="stat-label">③ One-click from any site</div>
          <div className="small">Drag this button to your bookmarks bar. On any job page (LinkedIn, Naukri, company site) click it after applying — it&apos;s tracked here with company & role detected.</div>
          <a ref={bookmarklet} className="btn primary" style={{ alignSelf: "flex-start", cursor: "grab" }} onClick={(e) => { e.preventDefault(); setToast("Drag it to your bookmarks bar instead of clicking"); }}>
            ＋ Track on StudySphere
          </a>
        </div>
      </div>

      <div>
        <button className="ghost" onClick={() => setShowManual(!showManual)}>{showManual ? "− Hide" : "＋ Add manually"}</button>
      </div>
      {showManual && (
        <form className="card row" onSubmit={add}>
          <input required placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <input required placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          <label className="small muted">Applied <input type="date" value={form.applied_on} onChange={(e) => setForm({ ...form, applied_on: e.target.value })} /></label>
          <label className="small muted">Next step <input type="date" value={form.next_step_on} onChange={(e) => setForm({ ...form, next_step_on: e.target.value })} /></label>
          <input type="url" placeholder="Job link (https://…)" value={form.link} onChange={(e) => setForm({ ...form, link: e.target.value })} />
          <button className="primary">Add</button>
        </form>
      )}
      {error && <p className="error">{error}</p>}

      <div className="kanban">
        {COLUMNS.map((col, idx) => {
          const items = data?.filter((a) => a.status === col.id) ?? [];
          return (
            <div key={col.id} className="card stack">
              <div className="row spread"><b>{col.label}</b><span className="pill">{items.length}</span></div>
              {items.map((a) => (
                <div key={a.id} className="card stack" style={{ padding: 10, background: "var(--panel-2)" }}>
                  <div className="row" style={{ flexWrap: "nowrap" }}>
                    <LogoChip name={a.company} size={28} />
                    <div style={{ minWidth: 0 }}><b>{a.company}</b><div className="muted small">{a.role}</div></div>
                  </div>
                  {a.applied_on && <div className="muted small">Applied {a.applied_on}</div>}
                  {a.next_step_on && <div className="small">Next: {a.next_step_on}</div>}
                  {a.link && <a className="small" href={a.link} target="_blank" rel="noopener noreferrer">Job posting ↗</a>}
                  <div className="row">
                    {idx > 0 && <button onClick={() => move(a, COLUMNS[idx - 1].id)}>◀</button>}
                    {idx < COLUMNS.length - 1 && <button onClick={() => move(a, COLUMNS[idx + 1].id)}>▶</button>}
                    <button className="ghost" title="Edit" onClick={() => rename(a)}>✎</button>
                    <button className="danger" onClick={() => remove(a)}>✕</button>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
