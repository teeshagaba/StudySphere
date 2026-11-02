"use client";

import { useEffect, useRef, useState } from "react";
import { post, useApi } from "@/lib/api";
import type { Question } from "@/lib/types";

type Mode = "hint" | "teacher" | "interviewer" | "debugger" | "planner";
interface Msg { role: "user" | "assistant"; content: string }

const MODES: { id: Mode; label: string; desc: string }[] = [
  { id: "hint", label: "Hint", desc: "One progressive hint at a time" },
  { id: "teacher", label: "Teacher", desc: "Learn the concept from first principles" },
  { id: "interviewer", label: "Interviewer", desc: "Mock FAANG interview" },
  { id: "debugger", label: "Debugger", desc: "Find bugs without spoilers" },
  { id: "planner", label: "Study Planner", desc: "Plan based on your weak areas" },
];

export default function MentorPage() {
  const questions = useApi<Question[]>("/dsa/questions");
  const [mode, setMode] = useState<Mode>("hint");
  const [questionId, setQuestionId] = useState<number | "">("");
  const [hintLevel, setHintLevel] = useState(1);
  const [code, setCode] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = Number(params.get("q"));
    if (id) setQuestionId(id);
    const m = params.get("mode");
    if (MODES.some((x) => x.id === m)) setMode(m as Mode);
    const topic = params.get("topic");
    if (topic) setInput(`Teach me ${topic.slice(0, 200)}`);
  }, []);

  const send = async (text: string, reveal = false) => {
    if (!text.trim()) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await post<{ reply: string; reveal_blocked: boolean; offline: boolean }>("/mentor/chat", {
        mode,
        messages: next.slice(-30),
        question_id: questionId || null,
        code: code.trim() || null,
        hint_level: hintLevel,
        reveal,
      });
      setOffline(res.offline);
      const note = res.reveal_blocked && !res.offline
        ? "\n\n🔒 Solution stays locked until you've made at least 2 attempts or spent 30+ minutes on this problem."
        : "";
      setMessages([...next, { role: "assistant", content: res.reply + note }]);
      if (mode === "hint") setHintLevel((l) => Math.min(3, l + 1));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      <h1>AI Mentor</h1>
      {offline && (
        <div className="card small" style={{ borderColor: "var(--medium)" }}>
          Running in <b>offline mode</b> (built-in hints, plans and checklists). For full AI chat, add a free key to <code>backend/.env</code>:
          e.g. <code>AI_BASE_URL=https://api.groq.com/openai/v1</code>, <code>AI_API_KEY=…</code>, <code>AI_MODEL=llama-3.3-70b-versatile</code> — or run Ollama locally — then restart the backend.
        </div>
      )}
      <div className="row">
        {MODES.map((m) => (
          <button key={m.id} className={mode === m.id ? "primary" : ""} title={m.desc}
            onClick={() => { setMode(m.id); setMessages([]); setHintLevel(1); }}>
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 2fr" }}>
        <div className="card stack">
          <label className="small muted">Problem (optional)</label>
          <select value={questionId} onChange={(e) => { setQuestionId(e.target.value ? Number(e.target.value) : ""); setHintLevel(1); }}>
            <option value="">— none —</option>
            {questions.data?.map((q) => <option key={q.id} value={q.id}>{q.title}</option>)}
          </select>
          {mode === "hint" && (
            <div className="small">Hint level: <b>{hintLevel}</b>/3 <span className="muted">(nudge → pattern → steps)</span></div>
          )}
          <label className="small muted">Your code (optional)</label>
          <textarea rows={12} value={code} onChange={(e) => setCode(e.target.value)} style={{ fontFamily: "monospace" }} />
          {questionId && (
            <button className="danger" disabled={busy} onClick={() => send("I've tried hard. Please show me the full solution.", true)}>
              Unlock solution
            </button>
          )}
        </div>

        <div className="card stack">
          <div className="chat">
            {messages.length === 0 && <p className="muted">{MODES.find((m) => m.id === mode)?.desc}. Ask anything to start.</p>}
            {messages.map((m, i) => <div key={i} className={`msg ${m.role}`}>{m.content}</div>)}
            {busy && <div className="msg assistant muted">Thinking…</div>}
            <div ref={bottom} />
          </div>
          {error && <div className="error">{error}</div>}
          <form className="row" onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <input style={{ flex: 1 }} value={input} onChange={(e) => setInput(e.target.value)}
              placeholder={mode === "hint" ? "I'm stuck on…" : mode === "planner" ? "Plan my next 7 days for Microsoft" : "Type a message"} />
            <button className="primary" disabled={busy}>Send</button>
          </form>
        </div>
      </div>
    </div>
  );
}
