"use client";

import { useEffect, useRef, useState } from "react";
import { post, useApi } from "@/lib/api";
import { useFocusMode } from "@/components/Shell";
import Toast from "@/components/ui";

interface Sessions { total_minutes: number; sessions: { id: number; kind: string; topic: string | null; duration_min: number; started_at: string }[] }

export default function FocusPage() {
  const setFocusMode = useFocusMode();
  const sessions = useApi<Sessions>("/focus/sessions?days=7");
  const [workMin, setWorkMin] = useState(25);
  const [breakMin, setBreakMin] = useState(5);
  const [topic, setTopic] = useState("");
  const [phase, setPhase] = useState<"work" | "break">("work");
  const [left, setLeft] = useState(25 * 60);
  const [running, setRunning] = useState(false);
  const [distractionFree, setDistractionFree] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const endAt = useRef<number>(0);

  useEffect(() => () => setFocusMode(false), [setFocusMode]);
  useEffect(() => setFocusMode(distractionFree), [distractionFree, setFocusMode]);
  useEffect(() => { if (!running) setLeft((phase === "work" ? workMin : breakMin) * 60); }, [workMin, breakMin, phase, running]);

  useEffect(() => {
    if (!running) return;
    endAt.current = Date.now() + left * 1000;
    const t = setInterval(() => {
      const remaining = Math.max(0, Math.round((endAt.current - Date.now()) / 1000));
      setLeft(remaining);
      if (remaining === 0) {
        clearInterval(t);
        setRunning(false);
        if (phase === "work") {
          post<{ xp_gained: number }>("/focus/sessions", { kind: "pomodoro", topic: topic || null, duration_min: workMin })
            .then((r) => { setToast(`Session logged! +${r.xp_gained} XP. Take a break.`); sessions.reload(); })
            .catch((e: Error) => setToast(e.message));
          setPhase("break");
        } else {
          setToast("Break over — back to work!");
          setPhase("work");
        }
      }
    }, 500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);

  useEffect(() => {
    document.title = running ? `${fmt(left)} · ${phase === "work" ? "Focus" : "Break"} — StudySphere` : "StudySphere";
  }, [left, running, phase]);

  return (
    <div className="stack" style={{ width: distractionFree ? 600 : undefined }}>
      {!distractionFree && <h1>Focus Mode</h1>}
      <div className="card stack" style={{ textAlign: "center" }}>
        <div className="muted">{phase === "work" ? "Focus" : "Break"}{topic && phase === "work" ? ` · ${topic}` : ""}</div>
        <div className="timer">{fmt(left)}</div>
        <div className="row" style={{ justifyContent: "center" }}>
          <button className="primary" onClick={() => setRunning(!running)}>{running ? "Pause" : "Start"}</button>
          <button onClick={() => { setRunning(false); setPhase("work"); setLeft(workMin * 60); }}>Reset</button>
          <button onClick={() => setDistractionFree(!distractionFree)}>{distractionFree ? "Exit distraction-free" : "Distraction-free"}</button>
        </div>
        {!running && !distractionFree && (
          <div className="row" style={{ justifyContent: "center" }}>
            <label className="small">Work <input type="number" min={5} max={180} value={workMin} onChange={(e) => setWorkMin(Number(e.target.value) || 25)} style={{ width: 70 }} /></label>
            <label className="small">Break <input type="number" min={1} max={60} value={breakMin} onChange={(e) => setBreakMin(Number(e.target.value) || 5)} style={{ width: 70 }} /></label>
            <input placeholder="What are you studying?" value={topic} maxLength={120} onChange={(e) => setTopic(e.target.value)} />
          </div>
        )}
      </div>

      {!distractionFree && (
        <div className="card">
          <h2>Last 7 days · {Math.round((sessions.data?.total_minutes ?? 0) / 6) / 10} h</h2>
          <table>
            <tbody>
              {sessions.data?.sessions.map((s) => (
                <tr key={s.id}>
                  <td className="small">{new Date(s.started_at).toLocaleString()}</td>
                  <td>{s.topic ?? <span className="muted">—</span>}</td>
                  <td className="small muted">{s.duration_min} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}

function fmt(sec: number) {
  return `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
}
