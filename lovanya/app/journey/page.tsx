"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Camera, Sparkles } from "lucide-react";
import { useLovanya } from "@/lib/store";

export default function Journey() {
  const checks = useLovanya((s) => s.checks);
  const items = useLovanya((s) => s.items);
  const wearCount = useLovanya((s) => s.wearCount);

  const avgScore = useMemo(
    () =>
      checks.length
        ? Math.round(checks.reduce((a, c) => a + c.score, 0) / checks.length)
        : null,
    [checks]
  );

  return (
    <div>
      <h1 className="font-display text-[34px] font-bold leading-tight text-ink">
        Your Journey
      </h1>
      <p className="mt-1.5 text-[14px] text-ink-soft">
        Every look you&rsquo;ve explored with Lovanya.
      </p>

      <div className="card mt-6 px-5 py-5">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="font-display text-2xl font-bold">{items.length}</p>
            <p className="text-[11.5px] text-ink-soft">pieces</p>
          </div>
          <div>
            <p className="font-display text-2xl font-bold">
              {checks.length + wearCount}
            </p>
            <p className="text-[11.5px] text-ink-soft">styling moments</p>
          </div>
          <div>
            <p className="font-display text-2xl font-bold">
              {avgScore ?? "—"}
            </p>
            <p className="text-[11.5px] text-ink-soft">avg confidence</p>
          </div>
        </div>
      </div>

      <h2 className="mt-7 text-[18px] font-semibold text-ink">Recent checks</h2>

      {checks.length === 0 ? (
        <div className="card mt-3 px-5 py-7 text-center">
          <p className="text-[13.5px] italic text-ink-soft">
            Your journey starts with one outfit check ♡
          </p>
          <Link
            href="/check"
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-br from-rosewood to-rosewood-deep px-5 py-2.5 text-[14px] font-semibold text-white shadow-lift active:scale-[0.97]"
          >
            <Camera size={16} /> Analyze a look
          </Link>
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          {checks.map((c) => (
            <div key={c.id} className="card flex items-center gap-4 px-5 py-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-rosewood to-gold font-display text-lg font-bold text-white">
                {c.score}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-semibold">
                  {c.headline}
                </p>
                <p className="text-[12.5px] text-ink-soft">
                  {new Date(c.at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </p>
              </div>
              <div className="flex gap-1">
                {c.palette.slice(0, 3).map((p, i) => (
                  <span
                    key={i}
                    className="h-4 w-4 rounded-full border border-line"
                    style={{ background: p }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-7 flex items-center justify-center gap-2 text-[12.5px] text-ink-faint">
        <Sparkles size={14} /> More chapters coming soon
      </div>
    </div>
  );
}
