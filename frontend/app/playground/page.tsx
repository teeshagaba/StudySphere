"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { post } from "@/lib/api";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type Lang = "cpp" | "java" | "python" | "javascript" | "go";
const TEMPLATES: Record<Lang, string> = {
  cpp: '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    int n; cin >> n;\n    cout << n * 2 << endl;\n}\n',
  java: 'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        System.out.println(n * 2);\n    }\n}\n',
  python: 'n = int(input())\nprint(n * 2)\n',
  javascript: 'const lines = require("fs").readFileSync(0, "utf8").trim().split("\\n");\nconsole.log(Number(lines[0]) * 2);\n',
  go: 'package main\n\nimport "fmt"\n\nfunc main() {\n    var n int\n    fmt.Scan(&n)\n    fmt.Println(n * 2)\n}\n',
};
const MONACO_LANG: Record<Lang, string> = { cpp: "cpp", java: "java", python: "python", javascript: "javascript", go: "go" };

interface RunResult { status: string; stdout: string | null; stderr: string | null; compile_output: string | null; time: string | null; memory: number | null }
interface Review { summary: string; time_complexity: string; space_complexity: string; issues: { line: number | null; severity: string; message: string }[]; suggestions: string[]; mode?: "ai" | "rules" }
interface Step { line: number; variables: Record<string, string>; output: string | null; explanation: string }

export default function PlaygroundPage() {
  const [lang, setLang] = useState<Lang>("python");
  const [code, setCode] = useState(TEMPLATES.python);
  const [stdin, setStdin] = useState("21");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [stepIdx, setStepIdx] = useState(0);
  const [traceMode, setTraceMode] = useState<"ai" | "traced">("ai");

  const act = async <T,>(name: string, path: string, body: object, done: (r: T) => void) => {
    setBusy(name);
    setError(null);
    try { done(await post<T>(path, body)); } catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  };

  const changeLang = (l: Lang) => { setLang(l); setCode(TEMPLATES[l]); setRun(null); setReview(null); setSteps([]); };
  const step = steps[stepIdx];

  return (
    <div className="stack">
      <div className="row spread">
        <h1>Coding Playground</h1>
        <div className="row">
          <select value={lang} onChange={(e) => changeLang(e.target.value as Lang)}>
            <option value="cpp">C++</option><option value="java">Java</option><option value="python">Python</option>
            <option value="javascript">JavaScript</option><option value="go">Go</option>
          </select>
          <button className="primary" disabled={!!busy} onClick={() => act<RunResult>("run", "/playground/run", { language: lang, code, stdin }, setRun)}>
            {busy === "run" ? "Running…" : "Run"}
          </button>
          <button disabled={!!busy} onClick={() => act<Review>("review", "/playground/review", { language: lang, code }, setReview)}>
            {busy === "review" ? "Reviewing…" : "Review"}
          </button>
          <button disabled={!!busy} onClick={() => act<{ steps: Step[]; mode?: "ai" | "traced" }>("dry", "/playground/dry-run", { language: lang, code, stdin }, (r) => { setSteps(r.steps); setStepIdx(0); setTraceMode(r.mode ?? "ai"); })}>
            {busy === "dry" ? "Tracing…" : "Dry run"}
          </button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="grid" style={{ gridTemplateColumns: "3fr 2fr" }}>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <Editor height="60vh" theme="vs-dark" language={MONACO_LANG[lang]} value={code}
            onChange={(v) => setCode(v ?? "")} options={{ minimap: { enabled: false }, fontSize: 14 }} />
        </div>
        <div className="stack">
          <div className="card">
            <h3>Input</h3>
            <textarea rows={4} value={stdin} onChange={(e) => setStdin(e.target.value)} style={{ fontFamily: "monospace" }} />
          </div>
          {run && (
            <div className="card">
              <div className="row spread"><h3>{run.status}</h3><span className="muted small">{run.time}s · {run.memory} KB</span></div>
              <pre style={{ whiteSpace: "pre-wrap" }}>{run.compile_output || run.stderr || run.stdout || "(no output)"}</pre>
            </div>
          )}
          {review && (
            <div className="card stack">
              <h3>{review.mode === "rules" ? "Code review (rule-based)" : "AI Review"}</h3>
              <div className="row"><span className="pill">Time: {review.time_complexity}</span><span className="pill">Space: {review.space_complexity}</span></div>
              <p>{review.summary}</p>
              {review.issues?.map((i, k) => (
                <div key={k} className="small"><span className={i.severity === "error" ? "Hard" : i.severity === "warning" ? "Medium" : "muted"}>[{i.severity}{i.line ? ` L${i.line}` : ""}]</span> {i.message}</div>
              ))}
              {review.suggestions?.length > 0 && <ul className="small">{review.suggestions.map((s, k) => <li key={k}>{s}</li>)}</ul>}
            </div>
          )}
        </div>
      </div>

      {steps.length > 0 && step && (
        <div className="card stack">
          <div className="row spread">
            <h3>Dry-run visualization <span className="muted small">({traceMode === "traced" ? "real execution trace" : "AI-simulated"})</span></h3>
            <div className="row">
              <button disabled={stepIdx === 0} onClick={() => setStepIdx(stepIdx - 1)}>◀ Prev</button>
              <span className="small">Step {stepIdx + 1}/{steps.length}</span>
              <button disabled={stepIdx === steps.length - 1} onClick={() => setStepIdx(stepIdx + 1)}>Next ▶</button>
            </div>
          </div>
          <div className="grid cols-2">
            <div style={{ background: "var(--panel-2)", borderRadius: 8, padding: 8, overflowX: "auto" }}>
              {code.split("\n").map((l, i) => (
                <div key={i} className={`code-line ${step.line === i + 1 ? "hl" : ""}`}>{String(i + 1).padStart(3)}  {l}</div>
              ))}
            </div>
            <div className="stack">
              <p>{step.explanation}</p>
              <table>
                <thead><tr><th>Variable</th><th>Value</th></tr></thead>
                <tbody>{Object.entries(step.variables ?? {}).map(([k, v]) => <tr key={k}><td>{k}</td><td><code>{String(v)}</code></td></tr>)}</tbody>
              </table>
              {step.output && <div className="small">Output: <code>{step.output}</code></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
