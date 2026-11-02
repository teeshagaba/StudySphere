"use client";

import Link from "next/link";
import { useApi } from "@/lib/api";
import type { Contest, Dashboard, JobsResponse, SheetSummary } from "@/lib/types";
import { CountUp, Heatmap, LogoChip, ProgressBar, Ring, Skeleton, Typewriter } from "@/components/ui";

function timeUntil(start: string) {
  const ms = new Date(start).getTime() - Date.now();
  if (ms <= 0) return "live";
  const d = Math.floor(ms / 86_400_000), h = Math.floor((ms / 3_600_000) % 24), m = Math.floor((ms / 60_000) % 60);
  return d ? `${d}d ${h}h` : `${h}h ${m}m`;
}

const DAILY_GOAL = 3;
const QUOTES = [
  "Consistency beats intensity — one problem a day compounds.",
  "Every expert was once a beginner who refused to quit.",
  "Don't count the problems you solve; make the problems you solve count.",
  "The best time to start was yesterday. The next best time is now.",
  "Stuck is just the step before the 'aha'.",
  "Code. Fail. Debug. Repeat. That's how engineers are made.",
  "Small daily improvements are the key to staggering long-term results.",
  "Your future offer letter is built one dry run at a time.",
  "Discipline is choosing between what you want now and what you want most.",
  "First, solve the problem. Then, write the code. — John Johnson",
  "It always seems impossible until it's done. — Nelson Mandela",
  "Talk is cheap. Show me the code. — Linus Torvalds",
  "Simplicity is the soul of efficiency. — Austin Freeman",
  "Make it work, make it right, make it fast. — Kent Beck",
  "A rejection today is data for the offer tomorrow.",
  "You don't have to be great to start, but you have to start to be great.",
  "The only bad attempt is the one you didn't make.",
  "Revise today what you solved last week — memory is a muscle.",
  "Hard problems are just easy problems you haven't broken down yet.",
  "Focus on the pattern, not the problem.",
  "Success is the sum of small efforts, repeated day in and day out. — Robert Collier",
];
const quoteOfDay = () => QUOTES[Math.floor(Date.now() / 86_400_000) % QUOTES.length];

export default function DashboardPage() {
  const { data, error } = useApi<Dashboard>("/analytics/dashboard");
  const sheets = useApi<SheetSummary[]>("/dsa/sheets");
  const contests = useApi<Contest[]>("/contests");
  const jobs = useApi<JobsResponse>("/jobs?limit=6&india=true&fresher=true");

  if (error) return <p className="error">{error}</p>;
  if (!data) return <div className="grid cols-4"><Skeleton height={140} count={4} /></div>;

  const { user, solved, streak } = data;
  const todayPct = Math.min(100, (data.solved_today / DAILY_GOAL) * 100);
  const maxMin = Math.max(60, ...data.study_week.map((d) => d.minutes));
  const topSheets = (sheets.data ?? [])
    .filter((s) => s.kind === "curated")
    .sort((a, b) => b.solved / (b.total || 1) - a.solved / (a.total || 1))
    .slice(0, 6);

  return (
    <div className="stack stagger">
      <div className="card hero glow">
        <div className="term-bar"><i /><i /><i /><span>~/studysphere — zsh</span></div>
        <div className="term-body">
          <div className="cmd"><b>$</b> whoami</div>
          <div className="out"><Typewriter text={`Welcome back, ${user.name}. Let's ship some code.`} /></div>
          <div className="cmd" style={{ marginTop: 8 }}>
            <b>$</b> status --today → <span className="Easy">{data.solved_today}/{DAILY_GOAL} solved</span> ·{" "}
            <span className="Medium">{data.revision_due} revisions due</span> ·{" "}
            <span style={{ color: "var(--accent-3)" }}>{streak.current}-day streak</span>
          </div>
          <div className="quote" style={{ marginTop: 10 }}>“{quoteOfDay()}”</div>
        </div>
      </div>

      <div className="grid cols-4 stagger">
        <div className="card hover row" style={{ flexWrap: "nowrap", gap: 16 }}>
          <Ring value={todayPct} label={`${data.solved_today}/${DAILY_GOAL}`} />
          <div>
            <div className="stat-label">Today&apos;s goal</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>
              {data.solved_today >= DAILY_GOAL ? "Goal crushed 🎉" : `Solve ${DAILY_GOAL - data.solved_today} more today`}
            </div>
            <Link href="/dsa" className="small">Pick a problem →</Link>
          </div>
        </div>
        <div className="card hover">
          <div className="stat-label">Problems solved</div>
          <div className="stat"><CountUp value={solved.total} /><span className="muted small"> / {data.total_questions}</span></div>
          <div className="row small" style={{ marginTop: 6 }}>
            <span className="diff Easy">{solved.Easy} E</span><span className="diff Medium">{solved.Medium} M</span><span className="diff Hard">{solved.Hard} H</span>
          </div>
        </div>
        <div className="card hover">
          <div className="stat-label">Current streak</div>
          <div className="stat"><CountUp value={streak.current} /> <span className="muted small">days</span></div>
          <div className="muted small">Longest: {streak.longest} days</div>
        </div>
        <div className="card hover">
          <div className="stat-label">Revisions due</div>
          <div className="stat"><CountUp value={data.revision_due} /></div>
          <Link href="/revision" className="small">Start revising →</Link>
        </div>
      </div>

      <div className="card">
        <div className="row spread"><h2>Activity</h2><span className="muted small mono">last 365 days</span></div>
        <Heatmap data={data.heatmap} />
      </div>

      <div className="grid cols-3">
        <div className="card">
          <div className="row spread"><h2>Upcoming contests</h2><Link href="/contests" className="small">all →</Link></div>
          {!contests.data && !contests.error && <Skeleton height={36} count={4} />}
          {contests.data?.slice(0, 5).map((c) => (
            <a key={`${c.platform}${c.url}${c.start}`} href={c.url} target="_blank" rel="noopener noreferrer" className="list-item" style={{ color: "inherit" }}>
              <LogoChip name={c.platform} size={30} />
              <div className="grow" style={{ minWidth: 0 }}>
                <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.name}</div>
                <div className="muted small">{c.platform}</div>
              </div>
              {timeUntil(c.start) === "live"
                ? <span className="pill live"><span className="dot-live" /> LIVE</span>
                : <span className="mono small" style={{ color: "var(--accent-3)" }}>{timeUntil(c.start)}</span>}
            </a>
          ))}
          {contests.data?.length === 0 && <div className="empty">no upcoming contests</div>}
        </div>

        <div className="card">
          <div className="row spread"><h2>Fresh openings</h2><Link href="/jobs" className="small">jobs board →</Link></div>
          {!jobs.data && !jobs.error && <Skeleton height={36} count={4} />}
          {jobs.data?.items.slice(0, 5).map((j) => (
            <a key={j.id} href={j.url} target="_blank" rel="noopener noreferrer" className="list-item" style={{ color: "inherit" }}>
              <LogoChip name={j.company} size={30} />
              <div className="grow" style={{ minWidth: 0 }}>
                <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{j.title}</div>
                <div className="muted small">{j.company} · {j.location}</div>
              </div>
            </a>
          ))}
          {jobs.data?.items.length === 0 && <div className="empty">no openings right now</div>}
        </div>

        <div className="card">
          <div className="row spread"><h2>Sheet progress</h2><Link href="/dsa" className="small">all sheets →</Link></div>
          {topSheets.map((s) => (
            <Link key={s.slug} href={`/dsa?sheet=${s.slug}`} style={{ color: "inherit", display: "block", marginBottom: 12 }}>
              <div className="row spread small"><span>{s.name}</span><span className="mono muted">{s.solved}/{s.total}</span></div>
              <ProgressBar value={s.total ? (s.solved / s.total) * 100 : 0} />
            </Link>
          ))}
        </div>
      </div>

      <div className="grid cols-3">
        <div className="card">
          <h2>Study hours (7d)</h2>
          <div className="row" style={{ alignItems: "flex-end", height: 120, flexWrap: "nowrap" }}>
            {data.study_week.map((d) => (
              <div key={d.date} style={{ flex: 1, textAlign: "center" }} title={`${d.minutes} min`}>
                <div style={{ height: (d.minutes / maxMin) * 100, minHeight: 3, background: "linear-gradient(180deg, var(--accent), var(--accent-3))", borderRadius: 6, transition: "height 1s" }} />
                <div className="muted small mono">{new Date(d.date).toLocaleDateString(undefined, { weekday: "narrow" })}</div>
              </div>
            ))}
          </div>
          <div className="muted small">Total: {data.study_hours_total} h</div>
        </div>
        <div className="card">
          <h2>Strong topics</h2>
          {data.strong_topics.length === 0 && <p className="muted small">Solve problems to build mastery.</p>}
          {data.strong_topics.map((m) => (
            <div key={m.topic} style={{ marginBottom: 10 }}>
              <div className="row spread small"><span>{m.topic}</span><span className="mono">{m.mastery}%</span></div>
              <ProgressBar value={m.mastery} />
            </div>
          ))}
        </div>
        <div className="card">
          <h2>Weak topics</h2>
          {data.weak_topics.map((m) => (
            <div key={m.topic} className="list-item small">
              <Link href={`/dsa?topic=${encodeURIComponent(m.topic)}`} className="grow">{m.topic}</Link>
              <span className="muted mono">{m.mastery}% · {m.solved}/{m.total}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Badges</h2>
          <div className="grid cols-4">
            {data.badges.map((b) => (
              <div key={b.code} title={b.description} style={{ opacity: b.earned_at ? 1 : 0.35, transition: "opacity .3s" }}>
                <div style={{ fontWeight: 700 }} className={b.earned_at ? "gradient-text" : ""}>{b.name}</div>
                <div className="muted small">{b.description}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="row spread"><h2>Placement funnel</h2><Link href="/career" className="small">tracker →</Link></div>
          <div className="row" style={{ flexWrap: "nowrap" }}>
            {Object.entries(data.career).map(([k, v]) => (
              <div key={k} className="card" style={{ flex: 1, textAlign: "center", padding: 10 }}>
                <div className="stat"><CountUp value={v} /></div>
                <div className="stat-label">{k}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
