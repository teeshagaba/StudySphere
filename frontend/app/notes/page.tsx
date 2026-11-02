"use client";

import { useState } from "react";
import { del, post, put, qs, useApi } from "@/lib/api";
import type { Note, Question } from "@/lib/types";

const KINDS: Note["kind"][] = ["question", "topic", "ai", "personal", "interview"];
const EMPTY = { kind: "personal" as Note["kind"], title: "", content: "", question_id: null as number | null, topic: "" };

export default function NotesPage() {
  const [kind, setKind] = useState<string>("");
  const [search, setSearch] = useState("");
  const notes = useApi<Note[]>(`/notes${qs({ kind, q: search })}`);
  const questions = useApi<Question[]>("/dsa/questions");
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [aiTarget, setAiTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = (n: Note) => {
    setEditing(n.id);
    setForm({ kind: n.kind, title: n.title, content: n.content, question_id: n.question_id, topic: n.topic ?? "" });
  };

  const save = async () => {
    setError(null);
    try {
      const body = { ...form, topic: form.topic || null };
      if (editing) await put(`/notes/${editing}`, body);
      else await post("/notes", body);
      setEditing(null);
      setForm(EMPTY);
      notes.reload();
    } catch (e) { setError((e as Error).message); }
  };

  const remove = async () => {
    if (!editing || !confirm("Delete this note?")) return;
    await del(`/notes/${editing}`);
    setEditing(null);
    setForm(EMPTY);
    notes.reload();
  };

  const generate = async () => {
    if (!aiTarget) return;
    setBusy(true);
    setError(null);
    try {
      const body = aiTarget.startsWith("q:") ? { question_id: Number(aiTarget.slice(2)) } : { topic: aiTarget.slice(2) };
      const note = await post<Note>("/notes/ai", body);
      notes.reload();
      open(note);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const topics = Array.from(new Set(questions.data?.flatMap((q) => q.topics) ?? [])).sort();

  return (
    <div className="stack">
      <h1>Notes</h1>
      <div className="grid" style={{ gridTemplateColumns: "1fr 2fr" }}>
        <div className="card stack">
          <div className="row">
            <span className={`pill ${kind === "" ? "active" : ""}`} style={{ cursor: "pointer" }} onClick={() => setKind("")}>all</span>
            {KINDS.map((k) => (
              <span key={k} className={`pill ${kind === k ? "active" : ""}`} style={{ cursor: "pointer" }} onClick={() => setKind(k)}>{k}</span>
            ))}
          </div>
          <input placeholder="Search notes…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button onClick={() => { setEditing(null); setForm(EMPTY); }}>+ New note</button>
          <div className="row">
            <select value={aiTarget} onChange={(e) => setAiTarget(e.target.value)} style={{ flex: 1 }}>
              <option value="">AI notes for…</option>
              <optgroup label="Topics">{topics.map((t) => <option key={t} value={`t:${t}`}>{t}</option>)}</optgroup>
              <optgroup label="Questions">{questions.data?.map((q) => <option key={q.id} value={`q:${q.id}`}>{q.title}</option>)}</optgroup>
            </select>
            <button className="primary" disabled={busy || !aiTarget} onClick={generate}>{busy ? "…" : "Generate"}</button>
          </div>
          <div>
            {notes.data?.map((n) => (
              <div key={n.id} onClick={() => open(n)} style={{ cursor: "pointer", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="row spread"><b>{n.title}</b><span className="pill">{n.kind}</span></div>
                <div className="muted small">{n.content.slice(0, 80)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card stack">
          <div className="row">
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Note["kind"] })}>
              {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input style={{ flex: 1 }} placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="row">
            <select value={form.question_id ?? ""} onChange={(e) => setForm({ ...form, question_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">Link to question…</option>
              {questions.data?.map((q) => <option key={q.id} value={q.id}>{q.title}</option>)}
            </select>
            <input placeholder="Topic" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} />
          </div>
          <textarea rows={22} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="Markdown supported…" style={{ fontFamily: "monospace" }} />
          {error && <div className="error">{error}</div>}
          <div className="row">
            <button className="primary" onClick={save} disabled={!form.title}>{editing ? "Update" : "Save"}</button>
            {editing && <button className="danger" onClick={remove}>Delete</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
