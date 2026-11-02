"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { TOKEN_KEY } from "@/lib/api";

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
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [focus, setFocus] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const isLogin = pathname === "/login";

  useEffect(() => setNavOpen(false), [pathname]);

  useEffect(() => {
    if (!isLogin && !localStorage.getItem(TOKEN_KEY)) router.replace("/login");
    else setReady(true);
  }, [isLogin, router]);

  if (isLogin) return <main className="main page" style={{ margin: "0 auto" }}>{children}</main>;
  if (!ready) return null;

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    router.replace("/login");
  };
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
          <div className="sidebar-foot">
            <button className="ghost" style={{ width: "100%", justifyContent: "center" }} onClick={logout}>Log out</button>
          </div>
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
