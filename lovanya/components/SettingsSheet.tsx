"use client";

import { useState } from "react";
import Sheet from "@/components/ui/Sheet";
import Chip from "@/components/ui/Chip";
import Button from "@/components/ui/Button";
import { useLovanya } from "@/lib/store";
import { MOODS, STYLE_VIBES } from "@/lib/types";

export default function SettingsSheet({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const profile = useLovanya((s) => s.profile);
  const setProfile = useLovanya((s) => s.setProfile);
  const seedCloset = useLovanya((s) => s.seedCloset);
  const startFresh = useLovanya((s) => s.startFresh);
  const [confirmFresh, setConfirmFresh] = useState(false);

  return (
    <Sheet open={open} onClose={onClose} title="Your details">
      <div className="space-y-7">
        <label className="block">
          <span className="text-[13px] font-semibold text-ink-soft">Name</span>
          <input
            value={profile.name}
            onChange={(e) => setProfile({ name: e.target.value })}
            className="mt-1.5 w-full rounded-2xl border border-line bg-porcelain px-4 py-3 font-display text-lg"
          />
        </label>

        <div>
          <p className="text-[13px] font-semibold text-ink-soft">Your vibes</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {STYLE_VIBES.map((v) => (
              <Chip
                key={v}
                selected={profile.vibes.includes(v)}
                onClick={() =>
                  setProfile({
                    vibes: profile.vibes.includes(v)
                      ? profile.vibes.filter((x) => x !== v)
                      : [...profile.vibes, v],
                  })
                }
              >
                {v}
              </Chip>
            ))}
          </div>
        </div>

        <div>
          <p className="text-[13px] font-semibold text-ink-soft">
            How you want to feel
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {MOODS.map((m) => (
              <Chip
                key={m.id}
                selected={profile.feeling === m.id}
                onClick={() => setProfile({ feeling: m.id })}
              >
                {m.label}
              </Chip>
            ))}
          </div>
        </div>

        <button
          onClick={() => setProfile({ modest: !profile.modest })}
          className="flex w-full items-center justify-between rounded-2xl border border-line bg-porcelain px-5 py-4 text-left"
        >
          <span>
            <span className="block text-[15px] font-semibold">
              Modest styling
            </span>
            <span className="mt-0.5 block text-[13px] text-ink-soft">
              Favor coverage-friendly pieces
            </span>
          </span>
          <span
            className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${
              profile.modest ? "bg-rosewood" : "bg-blush-deep"
            }`}
          >
            <span
              className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${
                profile.modest ? "left-6" : "left-1"
              }`}
            />
          </span>
        </button>

        <div className="border-t border-line pt-6">
          <p className="text-[13px] font-semibold text-ink-soft">Closet data</p>
          <div className="mt-3 space-y-2.5">
            <Button variant="soft" full onClick={() => { seedCloset(); onClose(); }}>
              Restore the demo closet
            </Button>
            {confirmFresh ? (
              <Button
                variant="ghost"
                full
                className="!text-rosewood-deep"
                onClick={() => {
                  startFresh();
                  setConfirmFresh(false);
                  onClose();
                }}
              >
                Tap again to erase everything
              </Button>
            ) : (
              <Button variant="ghost" full onClick={() => setConfirmFresh(true)}>
                Start fresh (empty closet)
              </Button>
            )}
          </div>
        </div>
      </div>
    </Sheet>
  );
}
