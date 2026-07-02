"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "motion/react";
import { BookHeart, Check, RotateCcw, Sparkles } from "lucide-react";
import AuraMessage from "@/components/AuraMessage";
import AuraOrb from "@/components/AuraOrb";
import PhotoCapture from "@/components/PhotoCapture";
import Button from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import Meter from "@/components/ui/Meter";
import ScoreRing from "@/components/ui/ScoreRing";
import { stylist } from "@/lib/ai";
import { THINKING_LINES } from "@/lib/aura";
import { downscaleImage, extractPalette } from "@/lib/color";
import { uid, useLovanya } from "@/lib/store";
import { OCCASIONS, type Occasion, type OutfitAnalysis } from "@/lib/types";
import { getTodayWeather } from "@/lib/weather";

function defaultOccasion(): Occasion {
  const day = new Date().getDay();
  return day === 0 || day === 6 ? "casual" : "work";
}

export default function OutfitCheck() {
  const profile = useLovanya((s) => s.profile);
  const recordCheck = useLovanya((s) => s.recordCheck);

  const [occasion, setOccasion] = useState<Occasion>(defaultOccasion);
  const [photo, setPhoto] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<OutfitAnalysis | null>(null);
  const [saved, setSaved] = useState(false);
  const [thinkingLine, setThinkingLine] = useState(0);
  const runRef = useRef(0);

  const weather = useMemo(() => getTodayWeather(), []);
  const stage = analysis ? "results" : photo ? "thinking" : "capture";

  useEffect(() => {
    if (stage !== "thinking") return;
    const t = setInterval(
      () => setThinkingLine((i) => (i + 1) % THINKING_LINES.length),
      1300
    );
    return () => clearInterval(t);
  }, [stage]);

  const analyze = async (dataUrl: string) => {
    const run = ++runRef.current;
    setPhoto(dataUrl);
    const palette = await extractPalette(dataUrl, 4);
    const result = await stylist.analyzeOutfit({
      palette,
      occasion,
      weather,
      profile,
    });
    if (runRef.current === run) setAnalysis(result);
  };

  const save = async () => {
    if (!analysis || !photo || saved) return;
    const thumb = await downscaleImage(photo, 180, 0.6);
    recordCheck({
      id: uid(),
      at: Date.now(),
      score: analysis.score,
      occasion,
      palette: analysis.palette,
      headline: analysis.headline,
      thumb,
    });
    setSaved(true);
  };

  const reset = () => {
    runRef.current++;
    setPhoto(null);
    setAnalysis(null);
    setSaved(false);
  };

  return (
    <div>
      {stage === "capture" && (
          <motion.div
            key="capture"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <header className="pt-2 text-center">
              <h1 className="font-display text-3xl">Outfit Check</h1>
              <p className="mt-1 text-sm text-ink-soft">
                A mirror selfie or a quick photo — I&rsquo;ll do the rest.
              </p>
            </header>

            <div className="no-scrollbar -mx-5 mt-5 flex gap-2 overflow-x-auto px-5 pb-1">
              {OCCASIONS.map((o) => (
                <Chip
                  key={o.id}
                  selected={occasion === o.id}
                  onClick={() => setOccasion(o.id)}
                >
                  {o.emoji} {o.label}
                </Chip>
              ))}
            </div>

            <div className="mt-4">
              <PhotoCapture
                facing="user"
                onCapture={analyze}
                hint="Photos are analyzed on your device and never uploaded."
              />
            </div>
          </motion.div>
        )}

        {stage === "thinking" && (
          <motion.div
            key="thinking"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex min-h-[70dvh] flex-col items-center justify-center text-center"
          >
            {photo && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={photo}
                alt=""
                className="h-40 w-32 rounded-3xl border-4 border-card object-cover shadow-soft"
              />
            )}
            <div className="mt-8">
              <AuraOrb size={56} />
            </div>
            <motion.p
              key={thinkingLine}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-5 font-display text-xl italic text-ink-soft"
            >
              {THINKING_LINES[thinkingLine]}
            </motion.p>
          </motion.div>
        )}

        {stage === "results" && analysis && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <header className="flex items-center gap-4 pt-2">
              {photo && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={photo}
                  alt="Your outfit"
                  className="h-24 w-20 rounded-2xl border-2 border-card object-cover shadow-soft"
                />
              )}
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rosewood">
                  Your palette today
                </p>
                <div className="mt-1.5 flex gap-1.5">
                  {analysis.palette.map((c, i) => (
                    <span
                      key={i}
                      className="h-6 w-6 rounded-full border-2 border-card shadow-sm"
                      style={{ background: c }}
                    />
                  ))}
                </div>
                <p className="mt-1.5 text-[12.5px] capitalize text-ink-soft">
                  {analysis.paletteNames.slice(0, 3).join(" · ")}
                </p>
              </div>
            </header>

            <div className="card flex flex-col items-center px-5 py-6 text-center">
              <ScoreRing value={analysis.score} />
              <h2 className="mt-4 font-display text-[22px] leading-snug">
                {analysis.headline}
              </h2>
            </div>

            <div className="card space-y-4 px-5 py-5">
              {analysis.breakdown.map((b) => (
                <Meter key={b.label} label={b.label} value={b.score} note={b.note} />
              ))}
            </div>

            <div className="card px-5 py-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sage-deep">
                What&rsquo;s working
              </p>
              <ul className="mt-3 space-y-2.5">
                {analysis.whatWorks.map((w, i) => (
                  <li key={i} className="flex gap-2.5 text-[14px] leading-snug">
                    <Check size={16} className="mt-0.5 shrink-0 text-sage-deep" />
                    {w}
                  </li>
                ))}
              </ul>
              <p className="mt-4 border-t border-line pt-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-gold">
                A gentle thought
              </p>
              <p className="mt-2 flex gap-2.5 text-[14px] leading-snug">
                <Sparkles size={16} className="mt-0.5 shrink-0 text-gold" />
                {analysis.gentleThought}
              </p>
            </div>

            <AuraMessage>{analysis.auraNote}</AuraMessage>

            <div className="flex gap-2.5 pb-2">
              <Button variant="soft" className="flex-1" onClick={reset}>
                <RotateCcw size={16} /> Again
              </Button>
              <Button className="flex-1" onClick={save} disabled={saved}>
                {saved ? (
                  <>
                    <Check size={17} /> Saved
                  </>
                ) : (
                  <>
                    <BookHeart size={17} /> Save to journal
                  </>
                )}
              </Button>
            </div>
          </motion.div>
        )}
    </div>
  );
}
