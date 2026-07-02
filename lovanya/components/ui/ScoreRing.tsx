"use client";

import { useEffect, useState } from "react";

export default function ScoreRing({
  value,
  size = 150,
  label = "confidence",
}: {
  value: number;
  size?: number;
  label?: string;
}) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const dur = 1200;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  const stroke = 10;
  const r = (size - stroke) / 2;
  const C = 2 * Math.PI * r;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#b16c7c" />
            <stop offset="100%" stopColor="#c2a077" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#f0e3df"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#ring-grad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C - (C * shown) / 100}
        />
      </svg>
      <div className="absolute text-center">
        <p className="font-display text-4xl leading-none">{shown}</p>
        <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-ink-soft">
          {label}
        </p>
      </div>
    </div>
  );
}
