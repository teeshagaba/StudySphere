"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { post, TOKEN_KEY } from "@/lib/api";

const NAV: { group: string; items: [string, string, string][] }[] = [
  { group: "Overview", items: [["/", "Dashboard", "⌂"]] },
  {
    group: "Practice",
    items: [
      ["/dsa", "DSA Sheets", "{}"],
      ["/revision", "Revision", "↻"],
      ["/contests", "Contests", "⚑"],
      ["/playground", "Playground", ">_"],
      ["/knowledge", "Knowledge Graph", "◈"],
    ],
  },
  {
    group: "Interview",
    items: [["/interview", "AI-Era Interview Prep", "◆"]],
  },
  {
    group: "Learn",
    items: [
      ["/resources", "Free Resources", "▤"],
      ["/learning", "AI Learning", "λ"],
      ["/notes", "Notes", "✎"],
      ["/mentor", "AI Mentor", "✦"],
      ["/focus", "Focus Mode", "◷"],
    ],
  },
  {
    group: "Career",
    items: [
      ["/jobs", "Jobs Board", "⌘"],
      ["/companies", "Companies", "▦"],
      ["/career", "Applications", "☰"],
    ],
  },
];

const FocusContext = createContext<(on: boolean) => void>(() => {});
export const useFocusMode = () => useContext(FocusContext);

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => setNavOpen(false), [pathname]);

  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) {
      setReady(true);
      return;
    }
    post<{ access_token: string }>("/auth/guest")
      .then((res) => {
        localStorage.setItem(TOKEN_KEY, res.access_token);
        setReady(true);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <main className="main page"><div className="error">Could not start session: {error}</div></main>;
  if (!ready) return <main className="main page muted">Loading…</main>;

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const path = pathname === "/" ? "" : pathname;

  return (
    <FocusContext.Provider value={setFocus}>
      <div className={`shell ${focus ? "focus-mode" : ""}`}>
        <aside className={`sidebar ${navOpen ? "open" : ""}`}>
          <Link href="/" className="brand" style={{ color: "inherit" }}>
            <div className="logo">S/</div>
            <span>StudySphere</span>
          </Link>
          <nav className="nav">
            {NAV.map(({ group, items }) => (
              <div key={group}>
                <div className="nav-group">{group}</div>
                {items.map(([href, label, icon]) => (
                  <Link key={href} href={href} className={isActive(href) ? "active" : ""}>
                    <span className="ico">{icon}</span>{label}
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </aside>
        {navOpen && <div className="backdrop" onClick={() => setNavOpen(false)} />}
        <div className="content">
          <header className="topbar">
            <div className="row" style={{ flexWrap: "nowrap" }}>
              <button className="ghost menu-btn" aria-label="Menu" onClick={() => setNavOpen(!navOpen)}>☰</button>
              <div className="prompt">
                <b>dev@studysphere</b>:<i>~{path}</i>$<span className="caret" />
              </div>
            </div>
            <div className="row muted small">
              <Link href="/dsa" className="btn ghost">Practice</Link>
              <Link href="/jobs" className="btn primary">Find jobs</Link>
            </div>
          </header>
          <main key={pathname} className="main page">{children}</main>
        </div>
      </div>
    </FocusContext.Provider>
  );
}
