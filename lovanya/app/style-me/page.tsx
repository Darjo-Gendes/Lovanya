"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Check, RefreshCw, Sparkles, Wand2 } from "lucide-react";
import AuraMessage from "@/components/AuraMessage";
import AuraOrb from "@/components/AuraOrb";
import ItemThumb from "@/components/ItemThumb";
import Button from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import { pairKey, stylist } from "@/lib/ai";
import { useLovanya } from "@/lib/store";
import {
  MOODS,
  OCCASIONS,
  type Mood,
  type Occasion,
  type Recommendation,
} from "@/lib/types";
import { getTodayWeather } from "@/lib/weather";

function defaultOccasion(): Occasion {
  const day = new Date().getDay();
  return day === 0 || day === 6 ? "casual" : "work";
}

export default function StyleMe() {
  const router = useRouter();
  const profile = useLovanya((s) => s.profile);
  const items = useLovanya((s) => s.items);
  const bias = useLovanya((s) => s.bias);
  const rejectedPairs = useLovanya((s) => s.rejectedPairs);
  const recordWear = useLovanya((s) => s.recordWear);
  const recordReject = useLovanya((s) => s.recordReject);

  const [occasion, setOccasion] = useState<Occasion>(defaultOccasion);
  const [mood, setMood] = useState<Mood>(profile.feeling);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [index, setIndex] = useState(0);
  const [thinking, setThinking] = useState(false);
  const [worn, setWorn] = useState(false);
  const runRef = useRef(0);

  const weather = useMemo(() => getTodayWeather(), []);

  const hasCore =
    items.some((i) => i.category === "dress") ||
    (items.some((i) => i.category === "top") &&
      items.some((i) => i.category === "bottom"));

  const compose = async (extraRejected: string[] = []) => {
    const run = ++runRef.current;
    setThinking(true);
    setWorn(false);
    const result = await stylist.recommendOutfits({
      wardrobe: items,
      context: {
        occasion,
        mood,
        weather,
        modest: profile.modest,
        bias,
        rejectedPairs: [...extraRejected, ...rejectedPairs],
      },
    });
    if (runRef.current !== run) return;
    setRecs(result);
    setIndex(0);
    setThinking(false);
  };

  const current = recs?.[index] ?? null;

  const another = () => {
    if (!recs || !current) return;
    recordReject(
      pairKey(current.items),
      current.items.map((i) => i.id)
    );
    if (index + 1 < recs.length) {
      setIndex(index + 1);
    } else {
      compose([pairKey(current.items)]);
    }
  };

  const wear = () => {
    if (!current) return;
    recordWear(current.items.map((i) => i.id));
    setWorn(true);
  };

  if (!hasCore) {
    return (
      <div className="space-y-6 pt-2">
        <h1 className="font-display text-3xl">Style Me</h1>
        <AuraMessage>
          I need a little more to work with — add a few tops and bottoms (or a
          dress) and I&rsquo;ll compose whole outfits for you.
        </AuraMessage>
        <Link
          href="/closet"
          className="block rounded-full bg-gradient-to-br from-rosewood to-rosewood-deep py-3.5 text-center font-semibold text-white shadow-lift"
        >
          Open my closet
        </Link>
      </div>
    );
  }

  return (
    <div>
      <header className="pt-2">
        <h1 className="font-display text-3xl">Style Me</h1>
        <p className="mt-0.5 text-sm text-ink-soft">
          Whole outfits from your own closet — with the why.
        </p>
      </header>

      {/* Context */}
      <div className="mt-5 space-y-3">
        <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5">
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
        <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5">
          {MOODS.map((m) => (
            <Chip key={m.id} selected={mood === m.id} onClick={() => setMood(m.id)}>
              {m.label}
            </Chip>
          ))}
        </div>
        <p className="text-[12.5px] text-ink-soft">
          {`${weather.tempC}° · ${weather.label} — I’ll dress you for it.`}
        </p>
      </div>

      {!recs && !thinking && (
        <div className="mt-8">
          <Button full onClick={() => compose()}>
            <Wand2 size={17} /> Compose my look
          </Button>
        </div>
      )}

      {thinking && (
          <motion.div
            key="thinking"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center py-16 text-center"
          >
            <AuraOrb size={52} />
            <p className="mt-5 font-display text-lg italic text-ink-soft">
              Composing something lovely…
            </p>
            <div className="aura-thinking mt-5 h-3 w-48 rounded-full" />
          </motion.div>
        )}

        {current && !thinking && !worn && (
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="mt-6 space-y-5"
          >
            <div className="card overflow-hidden">
              <div className="flex items-center justify-between px-5 pt-4">
                <h2 className="font-display text-2xl">{current.title}</h2>
                <span className="rounded-full bg-gradient-to-br from-rosewood to-gold px-3 py-1 font-display text-[15px] text-white shadow-lift">
                  {current.score}
                </span>
              </div>

              <div className="px-5 pb-5 pt-4">
                <div className="grid grid-cols-2 gap-2.5">
                  {current.items
                    .filter((i) =>
                      ["top", "bottom", "dress", "outerwear"].includes(i.category)
                    )
                    .map((i) => (
                      <div key={i.id}>
                        <ItemThumb
                          item={i}
                          className="border border-line bg-porcelain"
                        />
                        <p className="mt-1 line-clamp-1 text-[12px] font-medium text-ink-soft">
                          {i.name}
                        </p>
                      </div>
                    ))}
                </div>
                <div className="mt-2.5 grid grid-cols-3 gap-2.5">
                  {current.items
                    .filter(
                      (i) =>
                        !["top", "bottom", "dress", "outerwear"].includes(
                          i.category
                        )
                    )
                    .map((i) => (
                      <div key={i.id}>
                        <ItemThumb
                          item={i}
                          className="border border-line bg-porcelain"
                        />
                        <p className="mt-1 line-clamp-1 text-[11.5px] text-ink-soft">
                          {i.name}
                        </p>
                      </div>
                    ))}
                </div>
              </div>

              <div className="border-t border-line bg-porcelain/60 px-5 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rosewood">
                  Why this works
                </p>
                <ul className="mt-2.5 space-y-2">
                  {current.why.map((w, i) => (
                    <li key={i} className="flex gap-2.5 text-[13.5px] leading-snug">
                      <Sparkles size={14} className="mt-0.5 shrink-0 text-gold" />
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <AuraMessage>{current.auraNote}</AuraMessage>

            <div className="flex gap-2.5 pb-2">
              <Button variant="soft" className="flex-1" onClick={another}>
                <RefreshCw size={16} /> Another
              </Button>
              <Button className="flex-1" onClick={wear}>
                <Check size={17} /> I&rsquo;ll wear this
              </Button>
            </div>
          </motion.div>
        )}

        {worn && current && (
          <motion.div
            key="worn"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-8 space-y-5"
          >
            <div className="card flex flex-col items-center px-6 py-10 text-center">
              <AuraOrb size={60} />
              <h2 className="mt-5 font-display text-[26px] leading-snug">
                It&rsquo;s yours, {profile.name} ✨
              </h2>
              <p className="mt-2 max-w-[260px] text-[14px] text-ink-soft">
                I&rsquo;ve noted what you loved about today&rsquo;s look —
                tomorrow&rsquo;s suggestion will be even more you.
              </p>
            </div>
            <div className="flex gap-2.5">
              <Button variant="soft" className="flex-1" onClick={() => compose()}>
                Style another
              </Button>
              <Button className="flex-1" onClick={() => router.push("/")}>
                Done for today
              </Button>
            </div>
          </motion.div>
        )}
    </div>
  );
}
