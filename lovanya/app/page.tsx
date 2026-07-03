"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useLovanya } from "@/lib/store";
import { getTodayWeather } from "@/lib/weather";
import { greeting } from "@/lib/aura";
import SettingsSheet from "@/components/SettingsSheet";

/**
 * Home — ported 1:1 from public/prototype/lovanya-app.html (the reference
 * design the user approved). Styling lives under `.lv-home` in globals.css;
 * the dynamic slots (greeting, name, weather, saved-looks) read the store.
 */
export default function Today() {
  const profile = useLovanya((s) => s.profile);
  const checks = useLovanya((s) => s.checks);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const weather = useMemo(() => getTodayWeather(), []);

  const greetWord = greeting(""); // "Good morning" | "Good evening" | …
  const greetLine = greetWord.endsWith("?") ? greetWord : `${greetWord},`;
  const name = profile.name || "lovely";
  const topStyle = profile.vibes[0] || null;

  return (
    <div className="lv-home -mx-5">
      {/* ===== Hero ===== */}
      <div className="home-hero">
        <div className="home-deco" aria-hidden="true">
          <svg viewBox="0 0 64 64" fill="none" stroke="#D56F88" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="32" cy="32" r="6" />
            <path d="M32 26c-1-7 2-12 6-11s3 7-3 11M32 38c1 7-2 12-6 11s-3-7 3-11M26 32c-7-1-12 2-11 6s7 3 11-3M38 32c7-1 12 2 11 6s-7 3-11-3" />
          </svg>
        </div>

        <div className="home-head">
          <div className="home-logo">
            Lovanya
            <svg width="13" height="13" viewBox="0 0 24 24" fill="#D56F88">
              <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
            </svg>
          </div>
          <div className="home-actions">
            <button className="home-ic" aria-label="Menu and settings" onClick={() => setSettingsOpen(true)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3.5" y="5" width="17" height="16" rx="3" />
                <path d="M3.5 9.5h17M8 3.5v3M16 3.5v3" />
              </svg>
            </button>
            <button className="home-ic" aria-label="Notifications">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8.5a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17S18 14.5 18 8.5" />
                <path d="M10.4 20a2 2 0 0 0 3.2 0" />
              </svg>
              <span className="dot" />
            </button>
          </div>
        </div>

        <div className="home-greet">{greetLine}</div>
        <div className="home-name">
          {name}
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#E7A0B2" strokeWidth="1.6" style={{ marginTop: 11 }}>
            <path d="M12 20s-7-4.4-7-9.4A3.6 3.6 0 0 1 12 8a3.6 3.6 0 0 1 7-2.4C19 10.6 12 20 12 20z" />
          </svg>
        </div>
        <div className="home-sub">
          Let&rsquo;s create a beautiful day, inside and out.{" "}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="#E8B24A" style={{ verticalAlign: -2 }}>
            <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
          </svg>
        </div>
        <div className="home-weather">
          <svg width="30" height="24" viewBox="0 0 40 32" fill="none">
            <circle cx="12" cy="12" r="6" fill="#F6C45A" />
            <g stroke="#F1B64C" strokeWidth="2.2" strokeLinecap="round">
              <path d="M12 1v3M12 19v3M1 12h3M20 12h3M4.5 4.5l2 2M17.5 4.5l-2 2" />
            </g>
            <path d="M15.5 28c-3.1 0-5.5-2-5.5-4.6 0-2.5 2.2-4.5 4.9-4.3.9-2.7 3.4-4.6 6.4-4.6 3.6 0 6.6 2.7 6.9 6.2 2.1.2 3.7 1.9 3.7 4 0 2.4-2 4.3-4.5 4.3H15.5z" fill="#DAD2D0" />
          </svg>
          {weather.tempC}°C{"  •  "}{weather.label}
        </div>
      </div>

      {/* ===== Daily style check ===== */}
      <Link href="/check" className="home-check">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/prototype/outfit.jpg" alt="" />
        <div className="check-ico">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 8.5 6.5 4h11L21 8.5" />
            <rect x="3" y="8.5" width="18" height="11.5" rx="3.5" />
            <circle cx="12" cy="14" r="3.4" />
          </svg>
        </div>
        <div className="check-eye">DAILY STYLE CHECK</div>
        <div className="check-title">
          How are you
          <br />
          dressing today?
        </div>
        <div className="check-body">Upload your outfit and let Lovanya give you personalized insights.</div>
        <div className="check-btn">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="#fff">
            <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
          </svg>
          Analyze Today&rsquo;s Outfit
        </div>
      </Link>

      {/* Recommendations entry — distinct name so it doesn't clash with the
          Style Me tab (the analyze flow). */}
      <Link
        href="/style-me"
        className="mt-2.5 flex items-center justify-center gap-1.5 text-[13px] font-semibold text-rosewood"
        style={{ padding: "4px 22px 0" }}
      >
        or let me dress you from your closet
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
      </Link>

      {/* ===== Stats ===== */}
      <div className="home-stats">
        <div className="stat">
          <div className="si" style={{ background: "#FBE0E2" }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#E0764A">
              <path d="M12 2c1 3-1.4 4.4-1.4 6.9 0 1.4 1 2.4 1.5 2.9.8-.6 1.1-1.5 1.1-2.4 1.7 1.2 2.7 3 2.7 5.1A5.9 5.9 0 1 1 6.6 13c0-2 1-3.7 2.4-4.9C9.6 6.5 11 4.5 12 2z" />
            </svg>
          </div>
          <div className="sn">12</div>
          <div className="sl">Day Streak</div>
          <div className="sx">Keep it glowing!</div>
        </div>
        <div className="stat">
          <div className="si" style={{ background: "#EFE4F1" }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9B7FA6" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 7.5a2.2 2.2 0 1 1 2.2-2.2" />
              <path d="M12 7.5 3.8 14c-1 .8-.5 2.6.9 2.6h14.6c1.4 0 1.9-1.8.9-2.6L12 7.5z" />
            </svg>
          </div>
          <div className="sn">{checks.length}</div>
          <div className="sl">Looks Saved</div>
          <div className="sx">All time</div>
        </div>
        <div className="stat">
          <div className="si" style={{ background: "#E8F0D8" }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#8DA767">
              <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
            </svg>
          </div>
          <div className="sn" style={{ fontSize: 18, lineHeight: 1.05 }}>
            {topStyle ? (
              topStyle
            ) : (
              <>
                Casual
                <br />
                Chic
              </>
            )}
          </div>
          <div className="sx" style={{ marginTop: 6 }}>Your Top Style</div>
        </div>
      </div>

      {/* ===== Today's insight → History ===== */}
      <Link href="/journey" className="home-insight">
        <div className="e">TODAY&rsquo;S INSIGHT</div>
        <h3>Confidence is your best accessory.</h3>
        <p>You&rsquo;ve been choosing pieces that reflect you beautifully. Keep listening to yourself.</p>
        <div className="lk">
          View Your History{" "}
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#CE6E86" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 6l6 6-6 6" />
          </svg>
        </div>
      </Link>

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
