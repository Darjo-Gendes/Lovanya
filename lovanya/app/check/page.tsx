"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  BookHeart,
  Bookmark,
  BookOpen,
  Briefcase,
  Check,
  Heart,
  Home,
  Leaf,
  Share2,
  ShoppingBasket,
  Sparkles,
} from "lucide-react";
import PhotoCapture from "@/components/PhotoCapture";
import { stylist } from "@/lib/ai";
import { downscaleImage, extractPalette } from "@/lib/color";
import { findLikelyDuplicate } from "@/lib/dedup";
import { uid, useLovanya } from "@/lib/store";
import {
  OCCASIONS,
  type Occasion,
  type OutfitAnalysis,
} from "@/lib/types";
import { getTodayWeather } from "@/lib/weather";

/**
 * Style Me — the outfit-analysis flow, ported 1:1 from the analyze overlay in
 * public/prototype/lovanya-app.html (Occasion → Camera → Analyzing → Results
 * → Share card) and wired to the REAL analysis seam: on-device palette
 * extraction + stylist.analyzeOutfit (pipeline service when configured, local
 * mock otherwise). Styling lives under `.lv-az` in globals.css.
 */

type Stage = "occasion" | "camera" | "analyzing" | "results" | "share";

const OCC_ICON: Record<Occasion, typeof Briefcase> = {
  work: Briefcase,
  class: BookOpen,
  casual: Leaf,
  date: Heart,
  event: Sparkles,
  errands: ShoppingBasket,
};

const ANZ_STEPS = [
  "Understanding your style",
  "Examining color harmony",
  "Checking proportions",
  "Evaluating outfit balance",
  "Considering the occasion",
  "Almost done!",
];
const ANZ_TICK_MS = 520;

function Sparkle({ size = 12, color = "#CE6E86" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
    </svg>
  );
}

function defaultOccasion(): Occasion {
  const day = new Date().getDay();
  return day === 0 || day === 6 ? "casual" : "work";
}

export default function StyleMe() {
  const router = useRouter();
  const profile = useLovanya((s) => s.profile);
  const items = useLovanya((s) => s.items);
  const recordCheck = useLovanya((s) => s.recordCheck);
  const addItem = useLovanya((s) => s.addItem);

  const [stage, setStage] = useState<Stage>("occasion");
  const [occasion, setOccasion] = useState<Occasion>(defaultOccasion);
  // Free-text context from the prototype's design; analysis currently keys on
  // the occasion chip only.
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<OutfitAnalysis | null>(null);
  const [anzStep, setAnzStep] = useState(0);
  const [ringGo, setRingGo] = useState(false);
  const [barsGo, setBarsGo] = useState(false);
  const [saved, setSaved] = useState(false);
  const [ribboned, setRibboned] = useState(false);
  const [shareLbl, setShareLbl] = useState("Share Card");
  const runRef = useRef(0);

  const weather = useMemo(() => getTodayWeather(), []);

  // Analyzing screen: paced checklist + progress ring.
  useEffect(() => {
    if (stage !== "analyzing") return;
    setAnzStep(0);
    setRingGo(false);
    const raf = requestAnimationFrame(() =>
      requestAnimationFrame(() => setRingGo(true))
    );
    const t = setInterval(
      () => setAnzStep((s) => Math.min(s + 1, ANZ_STEPS.length)),
      ANZ_TICK_MS
    );
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(t);
    };
  }, [stage]);

  // Advance when both the pacing AND the real analysis are done.
  useEffect(() => {
    if (stage === "analyzing" && analysis && anzStep >= ANZ_STEPS.length) {
      setStage("results");
    }
  }, [stage, analysis, anzStep]);

  // Share screen: animate the strength bars in.
  useEffect(() => {
    if (stage !== "share") return;
    setBarsGo(false);
    const t = setTimeout(() => setBarsGo(true), 60);
    return () => clearTimeout(t);
  }, [stage]);

  const handleCapture = async (dataUrl: string) => {
    const run = ++runRef.current;
    setPhoto(dataUrl);
    setAnalysis(null);
    setStage("analyzing");
    try {
      const palette = await extractPalette(dataUrl, 4);
      const result = await stylist.analyzeOutfit({
        palette,
        occasion,
        weather,
        profile,
      });
      if (runRef.current === run) setAnalysis(result);
    } catch {
      if (runRef.current === run) setStage("camera");
    }
  };

  const cancelAnalyzing = () => {
    runRef.current++;
    setAnalysis(null);
    setStage("camera");
  };

  const retake = () => {
    runRef.current++;
    setPhoto(null);
    setAnalysis(null);
    setSaved(false);
    setRibboned(false);
    setStage("camera");
  };

  const restart = () => {
    runRef.current++;
    setPhoto(null);
    setAnalysis(null);
    setSaved(false);
    setRibboned(false);
    setNote("");
    setStage("occasion");
  };

  // Save to Journal: record the check AND file the look into the wardrobe
  // (identified via the real seam). Dedup gate: if it resembles an existing
  // piece we skip the add rather than silently merge or duplicate.
  const saveToJournal = async () => {
    if (!analysis || !photo) return;
    if (saved) {
      setStage("share");
      return;
    }
    setSaved(true);
    const [thumb, itemPhoto] = await Promise.all([
      downscaleImage(photo, 180, 0.6),
      downscaleImage(photo, 512, 0.72),
    ]);
    // File the garment FIRST so the look can record the canonical wardrobe id.
    let garmentIds: string[] = [];
    try {
      const draft = await stylist.identifyItem({
        palette: analysis.palette,
        modestDefault: profile.modest,
      });
      const match = findLikelyDuplicate(draft, items);
      if (match) {
        // The look wore an existing piece — link the canonical, never duplicate.
        garmentIds = [match.item.id];
      } else {
        const gid = uid();
        addItem({
          id: gid,
          name: draft.name,
          category: draft.category,
          colors: draft.colors,
          warmth: draft.warmth,
          formality: draft.formality,
          modest: draft.modest,
          photo: itemPhoto,
          timesWorn: 0,
          loved: false,
          addedAt: Date.now(),
        });
        garmentIds = [gid];
      }
    } catch {
      // Wardrobe filing is best-effort; the check itself is still recorded.
    }
    recordCheck({
      id: uid(),
      at: Date.now(),
      score: analysis.score,
      occasion,
      palette: analysis.palette,
      headline: analysis.headline,
      thumb,
      title: note.trim() || undefined,
      ribboned,
      garmentIds,
      breakdown: analysis.breakdown,
      whatWorks: analysis.whatWorks,
      gentleThought: analysis.gentleThought,
      auraNote: analysis.auraNote,
    });
    setStage("share");
  };

  const shareCard = () => {
    if (!analysis) return;
    if (navigator.share) {
      navigator
        .share({
          title: "My Lovanya Style Snapshot",
          text: `${analysis.headline} — ${analysis.score} style score, reviewed with Lovanya ♡`,
        })
        .catch(() => {});
    }
    setShareLbl("Shared ♡");
    setTimeout(() => setShareLbl("Share Card"), 1500);
  };

  const fmtDate = new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="lv-az" key={stage}>
      {/* ===== 1 · Occasion ===== */}
      {stage === "occasion" && (
        <div className="occ" style={{ paddingTop: 18 }}>
          <button className="aback" aria-label="Back to home" onClick={() => router.push("/")}>
            <ArrowLeft size={22} />
          </button>
          <h1 className="occ-title">
            Where are you going or what&rsquo;s the occasion?{" "}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E7A0B2" strokeWidth="1.7" style={{ verticalAlign: -2 }}>
              <path d="M12 20s-7-4.4-7-9.4A3.6 3.6 0 0 1 12 8a3.6 3.6 0 0 1 7-2.4C19 10.6 12 20 12 20z" />
            </svg>
          </h1>
          <p className="occ-sub">This helps Lovanya give more personalized insights.</p>
          <div className="occ-input">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Brunch with friends, Office meeting…"
            />
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C9A9AE" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3.5" y="5" width="17" height="16" rx="3" />
              <path d="M3.5 9.5h17M8 3.5v3M16 3.5v3" />
            </svg>
          </div>
          <p className="occ-label">Popular Suggestions</p>
          <div className="occ-grid">
            {OCCASIONS.map((o) => {
              const Icon = OCC_ICON[o.id];
              return (
                <button
                  key={o.id}
                  className={`occ-chip ${occasion === o.id ? "sel" : ""}`}
                  onClick={() => setOccasion(o.id)}
                >
                  <span className="occ-ico">
                    <Icon size={15} strokeWidth={1.8} />
                  </span>
                  {o.label}
                </button>
              );
            })}
          </div>
          <button className="abtn" style={{ marginTop: 24 }} onClick={() => setStage("camera")}>
            Continue
          </button>
          <button className="occ-skip" onClick={() => setStage("camera")}>
            Skip for now
          </button>
        </div>
      )}

      {/* ===== 2 · Camera ===== */}
      {stage === "camera" && (
        <div className="cam-wrap" style={{ paddingTop: 18 }}>
          <button className="aback" aria-label="Back to occasion" onClick={() => setStage("occasion")}>
            <ArrowLeft size={22} />
          </button>
          <p className="eyebrow" style={{ marginTop: 8 }}>
            <Sparkle /> Daily Style Check
          </p>
          <h1 className="occ-title" style={{ marginTop: 6 }}>
            Show me today&rsquo;s look
          </h1>
          <p className="occ-sub">
            Stand back, relax, and let natural light do the magic{" "}
            <Sparkle size={12} color="#E8B24A" />
          </p>
          <div style={{ marginTop: 18 }}>
            <PhotoCapture
              facing="user"
              onCapture={handleCapture}
              hint="Analyzed on your device — never uploaded."
            />
          </div>
        </div>
      )}

      {/* ===== 3 · Analyzing ===== */}
      {stage === "analyzing" && (
        <div className="anz" style={{ paddingTop: 18 }}>
          <button className="aback" aria-label="Cancel analysis" onClick={cancelAnalyzing}>
            <ArrowLeft size={22} />
          </button>
          <h1 className="anz-title">
            Analyzing your look&hellip;{" "}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E7A0B2" strokeWidth="1.7">
              <path d="M21 11.5a8.4 8.4 0 0 1-12 7.6L3 21l2-5.4A8.4 8.4 0 1 1 21 11.5z" />
            </svg>
          </h1>
          <div className="anz-ringwrap">
            <svg className="anz-ring" width="130" height="130" viewBox="0 0 130 130">
              <circle cx="65" cy="65" r="58" fill="none" stroke="#F6DCDE" strokeWidth="9" />
              <circle
                className="anz-prog"
                cx="65"
                cy="65"
                r="58"
                fill="none"
                stroke="#D56F88"
                strokeWidth="9"
                strokeLinecap="round"
                strokeDasharray="364.4"
                style={{ strokeDashoffset: ringGo ? 0 : 364.4 }}
              />
            </svg>
            <div className="anz-spark">
              <Sparkle size={40} color="#D56F88" />
            </div>
          </div>
          <ul className="anz-list">
            {ANZ_STEPS.map((s, i) => (
              <li
                key={s}
                className={`anz-item ${i < anzStep ? "done" : i === anzStep ? "act" : ""}`}
              >
                <span className="adot">
                  <Check size={9} strokeWidth={3.5} />
                </span>
                {s}
              </li>
            ))}
          </ul>
          <div className="anz-note">
            <Sparkle size={16} color="#D56F88" />
            Lovanya looks at styling, coordination, and presentation — not perfection.
          </div>
        </div>
      )}

      {/* ===== 4 · Results ===== */}
      {stage === "results" && analysis && photo && (
        <div>
          <div className="res-hero">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photo} alt="Your outfit" />
            <div className="ov" />
            <button className="res-hbtn" style={{ left: 18 }} aria-label="Retake photo" onClick={retake}>
              <ArrowLeft size={20} />
            </button>
            <button
              className="res-hbtn"
              style={{ right: 18 }}
              aria-label={ribboned ? "Marked as memorable" : "Mark as memorable"}
              onClick={() => setRibboned((v) => !v)}
            >
              <Bookmark size={19} fill={ribboned ? "#D56F88" : "none"} color="#D56F88" strokeWidth={1.8} />
            </button>
            <div className="res-view">
              <Sparkle size={13} color="#D56F88" /> {analysis.score} · Style Score
            </div>
          </div>
          <div className="res-body">
            <p className="eyebrow">
              <Sparkle /> Style Reflection
            </p>
            <h2 className="res-verdict">{analysis.headline}</h2>
            <p className="res-sub">{analysis.auraNote}</p>

            <p className="eyebrow" style={{ marginTop: 24 }}>
              <Sparkle color="#8DA767" /> What Works Well
            </p>
            <ul className="res-list">
              {analysis.whatWorks.map((w, i) => (
                <li key={i} className="res-li">
                  <span className="ic" style={{ background: "var(--sagebg2)", color: "var(--sage2)" }}>
                    <Check size={16} strokeWidth={2.2} />
                  </span>
                  <p>{w}</p>
                </li>
              ))}
            </ul>

            <p className="eyebrow" style={{ marginTop: 24 }}>
              <Sparkle color="#E8B24A" /> Opportunities To Elevate
            </p>
            <ul className="res-list">
              <li className="res-li">
                <span className="ic" style={{ background: "var(--blush3)", color: "var(--pink)" }}>
                  <Sparkles size={16} strokeWidth={1.9} />
                </span>
                <p>{analysis.gentleThought}</p>
              </li>
            </ul>

            <div className="res-actions">
              <button
                className="res-heart"
                aria-label={ribboned ? "Marked as memorable" : "Mark as memorable"}
                onClick={() => setRibboned((v) => !v)}
              >
                <Bookmark size={22} fill={ribboned ? "currentColor" : "none"} strokeWidth={1.8} />
              </button>
              <button className="abtn" onClick={saveToJournal}>
                <BookHeart size={18} strokeWidth={1.9} />
                {saved ? "View Style Card" : "Save to Journal"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== 5 · Share card ===== */}
      {stage === "share" && analysis && photo && (
        <div className="snap-wrap" style={{ paddingTop: 18 }}>
          <button className="aback" aria-label="Back to results" onClick={() => setStage("results")}>
            <ArrowLeft size={22} />
          </button>
          <div className="snap" style={{ marginTop: 8 }}>
            <div className="snap-top">
              <span className="snap-logo">Lovanya</span>
              <span className="snap-tag">Style Snapshot</span>
            </div>
            <div className="snap-h">
              <h3>My Style Snapshot</h3>
              <div className="snap-date">{fmtDate}</div>
            </div>
            <div className="snap-photo">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo} alt="Your outfit" />
              <div className="snap-imp">
                <div className="e">Overall Impression</div>
                <div className="t">{analysis.headline}</div>
                <div className="s">{analysis.paletteNames.slice(0, 3).join(" · ")}</div>
              </div>
            </div>
            <div className="snap-strength">
              <p className="eyebrow">Style Strengths</p>
              {analysis.breakdown.map((b) => (
                <div key={b.label} className="bar-row">
                  <span className="lbl">
                    <Sparkle size={12} color="#D56F88" />
                    {b.label}
                  </span>
                  <span className="bar-track">
                    <span
                      className="bar-fill"
                      style={{ width: barsGo ? `${b.score}%` : "0%" }}
                    />
                  </span>
                  <span className="bar-val">{b.score}%</span>
                </div>
              ))}
            </div>
            <div className="snap-refl">
              <p className="eyebrow">Style Reflection</p>
              <p>{analysis.gentleThought}</p>
            </div>
            <div className="snap-foot">
              <div className="f1">Captured with Lovanya</div>
              <div className="f2">Your personal AI stylist &amp; style journal</div>
            </div>
          </div>
          <button className="abtn" style={{ marginTop: 18 }} onClick={shareCard}>
            <Share2 size={18} strokeWidth={1.9} />
            {shareLbl}
          </button>
          <button className="abtn soft" style={{ marginTop: 11 }} onClick={() => router.push("/")}>
            <Home size={18} strokeWidth={1.9} />
            Back to Home
          </button>
          <button className="occ-skip" style={{ marginTop: 10 }} onClick={restart}>
            Style another look
          </button>
        </div>
      )}
    </div>
  );
}
