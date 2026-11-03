"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, post, TOKEN_KEY, useApi } from "@/lib/api";

type Mode = "save" | "login";

export default function LoginPage() {
  const router = useRouter();
  const me = useApi<{ is_guest: boolean }>("/auth/me");
  const [mode, setMode] = useState<Mode>("save");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("mode") === "login") setMode("login");
  }, []);

  useEffect(() => {
    if (me.data && !me.data.is_guest) router.replace("/");
  }, [me.data, router]);

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
          : await post<{ access_token: string }>("/auth/claim", form);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      window.location.href = "/";
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "6vh auto" }} className="card glow hero">
      <div className="term-bar"><i /><i /><i /><span>~/studysphere — {mode === "save" ? "save progress" : "login"}</span></div>
      <div className="stack" style={{ padding: 22 }}>
        <h1><span className="gradient-text">{mode === "save" ? "Save your progress" : "Welcome back"}</span></h1>
        <p className="muted">
          {mode === "save"
            ? "Create an account to keep everything you've done so far and use it on any device."
            : "Log in to continue on this device. Your current guest progress will not be merged."}
        </p>
        <form onSubmit={submit} className="stack">
          {mode === "save" && (
            <input placeholder="Name" required maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: "100%" }} />
          )}
          <input type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} style={{ width: "100%" }} />
          <input type="password" placeholder="Password (min 8 chars)" required minLength={8} maxLength={72} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={{ width: "100%" }} />
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy} style={{ width: "100%" }}>
            {mode === "save" ? "Create account" : "Log in"}
          </button>
        </form>
        <button onClick={() => setMode(mode === "save" ? "login" : "save")} style={{ width: "100%" }}>
          {mode === "save" ? "Already have an account? Log in" : "New here? Save your guest progress"}
        </button>
      </div>
    </div>
  );
}
