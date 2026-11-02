"use client";

import { useEffect, useState } from "react";

export default function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!message) return;
    setVisible(true);
    const t = setTimeout(() => { setVisible(false); onDone(); }, 4000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);
  return visible && message ? <div className="toast">{message}</div> : null;
}

export function ProgressBar({ value }: { value: number }) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const t = requestAnimationFrame(() => setW(Math.max(0, Math.min(100, value))));
    return () => cancelAnimationFrame(t);
  }, [value]);
  return <div className="bar"><div style={{ width: `${w}%` }} /></div>;
}

export function CountUp({ value, duration = 900 }: { value: number; duration?: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{n.toLocaleString()}</>;
}

export function Ring({ value, size = 76, stroke = 7, label }: { value: number; size?: number; stroke?: number; label?: React.ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [offset, setOffset] = useState(c);
  useEffect(() => {
    const v = Number.isFinite(value) ? value : 0;
    const t = requestAnimationFrame(() => setOffset(c * (1 - Math.max(0, Math.min(100, v)) / 100)));
    return () => cancelAnimationFrame(t);
  }, [value, c]);
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--accent)" /><stop offset="100%" stopColor="var(--accent-3)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--panel-3)" strokeWidth={stroke} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke="url(#ringGrad)" strokeWidth={stroke} fill="none"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} />
      </svg>
      <div className="ring-label" style={{ fontSize: size / 5 }}>{label ?? `${Math.round(value)}%`}</div>
    </div>
  );
}

export function Typewriter({ text, speed = 35 }: { text: string; speed?: number }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    let k = 0;
    setI(0);
    const t = setInterval(() => {
      k += 1;
      setI(k);
      if (k >= text.length) clearInterval(t);
    }, speed);
    return () => clearInterval(t);
  }, [text, speed]);
  return <>{text.slice(0, i)}<span className="caret" /></>;
}

export function Skeleton({ height = 90, count = 1 }: { height?: number; count?: number }) {
  return <>{Array.from({ length: count }, (_, i) => <div key={i} className="skeleton" style={{ height }} />)}</>;
}

export function PageHead({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1><span className="gradient-text">#</span> {title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="row">{children}</div>}
    </div>
  );
}

const CHIP_COLORS = ["#2ee6a6", "#38bdf8", "#8b5cf6", "#fbbf24", "#f472b6", "#fb923c", "#a3e635"];
export function LogoChip({ name, size = 38 }: { name: string; size?: number }) {
  const h = [...name].reduce((a, ch) => a + ch.charCodeAt(0), 0);
  const bg = CHIP_COLORS[h % CHIP_COLORS.length];
  return (
    <div className="logo-chip" style={{ width: size, height: size, background: `linear-gradient(135deg, ${bg}, ${bg}99)` }}>
      {name.replace(/[^A-Za-z0-9]/g, "").slice(0, 2).toUpperCase()}
    </div>
  );
}

export function Heatmap({ data }: { data: { date: string; count: number }[] }) {
  const counts = new Map(data.map((d) => [d.date, d.count]));
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 364 - today.getDay());
  const cells = [];
  for (let d = new Date(start); d <= today; d.setDate(d.getDate() + 1)) {
    const key = d.toISOString().slice(0, 10);
    const c = counts.get(key) ?? 0;
    const lvl = c === 0 ? "" : c < 2 ? "l1" : c < 4 ? "l2" : c < 7 ? "l3" : "l4";
    cells.push(<div key={key} className={lvl} title={`${key}: ${c} activities`} />);
  }
  return <div className="heatmap">{cells}</div>;
}
