"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, post, TOKEN_KEY } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === "login"
          ? await api<{ access_token: string }>("/auth/login", {
              method: "POST",
              body: new URLSearchParams({ username: form.email, password: form.password }),
            })
          : await post<{ access_token: string }>("/auth/register", form);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      router.replace("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "12vh auto" }} className="card glow hero">
      <div className="term-bar"><i /><i /><i /><span>~/studysphere — login</span></div>
      <div className="stack" style={{ padding: 22 }}>
      <h1><span className="gradient-text">StudySphere</span><span className="caret" /></h1>
      <p className="muted">DSA sheets, contests, jobs, free resources and an AI mentor in one place.</p>
      <form onSubmit={submit} className="stack">
        {mode === "register" && (
          <input placeholder="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: "100%" }} />
        )}
        <input type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} style={{ width: "100%" }} />
        <input type="password" placeholder="Password (min 8 chars)" required minLength={8} maxLength={72} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={{ width: "100%" }} />
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy} style={{ width: "100%" }}>
          {mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
      <button onClick={() => setMode(mode === "login" ? "register" : "login")} style={{ width: "100%" }}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Log in"}
      </button>
      </div>
    </div>
  );
}
