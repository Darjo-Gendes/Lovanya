"use client";

import { useState } from "react";
import { Setting2 } from "iconsax-react";
import AuraOrb from "@/components/AuraOrb";
import SettingsSheet from "@/components/SettingsSheet";
import { useLovanya } from "@/lib/store";
import { MOODS } from "@/lib/types";

export default function Profile() {
  const profile = useLovanya((s) => s.profile);
  const items = useLovanya((s) => s.items);
  const checks = useLovanya((s) => s.checks);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const feeling = MOODS.find((m) => m.id === profile.feeling)?.label;

  return (
    <div>
      <div className="flex items-center justify-between pt-1">
        <h1 className="font-display text-[34px] font-bold leading-tight text-ink">
          Profile
        </h1>
        <button
          onClick={() => setSettingsOpen(true)}
          aria-label="Settings"
          className="flex h-[42px] w-[42px] items-center justify-center rounded-[13px] bg-card text-ink-soft shadow-soft active:scale-95"
        >
          <Setting2 size={20} />
        </button>
      </div>

      <div className="card mt-6 flex flex-col items-center px-6 py-8 text-center">
        <AuraOrb size={64} />
        <p className="mt-4 font-display text-2xl font-semibold text-ink">
          {profile.name || "Lovely"}
        </p>
        {feeling && (
          <p className="mt-1 text-[13.5px] text-ink-soft">
            Feeling {feeling.toLowerCase()} today
          </p>
        )}
        <div className="mt-5 flex w-full justify-around border-t border-line pt-5">
          <div>
            <p className="font-display text-xl font-bold">{items.length}</p>
            <p className="text-[11.5px] text-ink-soft">pieces</p>
          </div>
          <div>
            <p className="font-display text-xl font-bold">{checks.length}</p>
            <p className="text-[11.5px] text-ink-soft">checks</p>
          </div>
          <div>
            <p className="font-display text-xl font-bold">
              {items.filter((i) => i.loved).length}
            </p>
            <p className="text-[11.5px] text-ink-soft">loved</p>
          </div>
        </div>
      </div>

      {profile.vibes.length > 0 && (
        <div className="mt-6">
          <p className="text-[13px] font-semibold text-ink-soft">Your vibes</p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {profile.vibes.map((v) => (
              <span
                key={v}
                className="rounded-full bg-blush px-4 py-2 text-[13px] font-medium text-rosewood-deep"
              >
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={() => setSettingsOpen(true)}
        className="mt-6 flex w-full items-center justify-between rounded-2xl border border-line bg-card px-5 py-4 text-left active:scale-[0.99]"
      >
        <span>
          <span className="block text-[15px] font-semibold">Your details</span>
          <span className="mt-0.5 block text-[13px] text-ink-soft">
            Name, vibes, modest styling &amp; closet data
          </span>
        </span>
        <Setting2 size={18} className="text-ink-faint" />
      </button>

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
