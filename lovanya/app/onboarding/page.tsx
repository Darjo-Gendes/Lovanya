"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import AuraOrb from "@/components/AuraOrb";
import Button from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import { useLovanya } from "@/lib/store";
import { MOODS, STYLE_VIBES, type Mood } from "@/lib/types";

export default function Onboarding() {
  const router = useRouter();
  const setProfile = useLovanya((s) => s.setProfile);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [vibes, setVibes] = useState<string[]>([]);
  const [modest, setModest] = useState(false);
  const [feeling, setFeeling] = useState<Mood>("confident");

  const finish = () => {
    setProfile({
      name: name.trim() || "lovely",
      vibes,
      modest,
      feeling,
      onboarded: true,
    });
    router.replace("/");
  };

  const fade = {
    initial: { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -14 },
    transition: { duration: 0.32 },
  };

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      {/* progress dots */}
      <div className="mb-10 flex justify-center gap-2 pt-2">
        {[0, 1, 2, 3].map((i) => (
          <span
            key={i}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === step ? "w-7 bg-rosewood" : "w-1.5 bg-blush-deep"
            }`}
          />
        ))}
      </div>

      {step === 0 && (
          <motion.div key="s0" {...fade} className="flex flex-1 flex-col items-center justify-center text-center">
            <AuraOrb size={88} />
            <h1 className="mt-8 font-display text-4xl leading-tight">
              Loványa
            </h1>
            <p className="mt-1 text-sm uppercase tracking-[0.22em] text-rosewood">
              your best friend in fashion
            </p>
            <p className="mt-6 max-w-[260px] font-display text-lg italic leading-relaxed text-ink-soft">
              &ldquo;I&rsquo;m Aura. I&rsquo;m here to make getting dressed the
              easiest part of your day.&rdquo;
            </p>
            <div className="mt-12 w-full">
              <Button full onClick={() => setStep(1)}>
                Lovely to meet you <ArrowRight size={17} />
              </Button>
            </div>
          </motion.div>
        )}

        {step === 1 && (
          <motion.div key="s1" {...fade} className="flex flex-1 flex-col">
            <h2 className="font-display text-3xl leading-snug">
              What should I<br />call you?
            </h2>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="mt-8 w-full rounded-2xl border border-line bg-card px-5 py-4 font-display text-xl placeholder:text-ink-faint focus:border-rosewood"
              onKeyDown={(e) => e.key === "Enter" && name.trim() && setStep(2)}
            />
            <div className="mt-auto pt-10">
              <Button full disabled={!name.trim()} onClick={() => setStep(2)}>
                Continue <ArrowRight size={17} />
              </Button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div key="s2" {...fade} className="flex flex-1 flex-col">
            <h2 className="font-display text-3xl leading-snug">
              Which feelings are<br />
              <em className="text-rosewood">your</em> style?
            </h2>
            <p className="mt-2 text-sm text-ink-soft">
              Pick any that speak to you — I&rsquo;ll learn the rest.
            </p>
            <div className="mt-7 flex flex-wrap gap-2.5">
              {STYLE_VIBES.map((v) => (
                <Chip
                  key={v}
                  selected={vibes.includes(v)}
                  onClick={() =>
                    setVibes((cur) =>
                      cur.includes(v)
                        ? cur.filter((x) => x !== v)
                        : [...cur, v]
                    )
                  }
                >
                  {v}
                </Chip>
              ))}
            </div>
            <div className="mt-auto pt-10">
              <Button full onClick={() => setStep(3)}>
                Continue <ArrowRight size={17} />
              </Button>
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div key="s3" {...fade} className="flex flex-1 flex-col">
            <h2 className="font-display text-3xl leading-snug">
              And how do you want
              <br />
              to <em className="text-rosewood">feel</em>?
            </h2>
            <div className="mt-7 flex flex-wrap gap-2.5">
              {MOODS.map((m) => (
                <Chip
                  key={m.id}
                  selected={feeling === m.id}
                  onClick={() => setFeeling(m.id)}
                >
                  {m.label}
                </Chip>
              ))}
            </div>

            <button
              onClick={() => setModest((m) => !m)}
              className="card mt-9 flex w-full items-center justify-between px-5 py-4 text-left"
            >
              <span>
                <span className="block text-[15px] font-semibold">
                  Modest styling
                </span>
                <span className="mt-0.5 block text-[13px] text-ink-soft">
                  I&rsquo;ll favor coverage-friendly pieces
                </span>
              </span>
              <span
                className={`relative h-7 w-12 rounded-full transition-colors ${
                  modest ? "bg-rosewood" : "bg-blush-deep"
                }`}
              >
                <span
                  className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${
                    modest ? "left-6" : "left-1"
                  }`}
                />
              </span>
            </button>

            <div className="mt-auto pt-10">
              <Button full onClick={finish}>
                Let&rsquo;s begin ✨
              </Button>
            </div>
          </motion.div>
        )}
    </div>
  );
}
