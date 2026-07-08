"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { useEffect, useState } from "react";
import type {
  CheckRecord,
  ItemVariant,
  Profile,
  WardrobeItem,
} from "./types";
import { SEED_ITEMS } from "./seed";
import { colorFamily } from "./color";

interface LovanyaState {
  profile: Profile;
  items: WardrobeItem[];
  checks: CheckRecord[];
  /** Preference memory: color-family -> bias weight. */
  bias: Record<string, number>;
  /** Core-piece combos the user said no to. */
  rejectedPairs: string[];
  wearCount: number;
  seeded: boolean;

  setProfile: (p: Partial<Profile>) => void;
  addItem: (item: WardrobeItem) => void;
  /** User confirmed "same piece" — attach the re-upload to the canonical item. */
  mergeVariant: (canonicalId: string, variant: ItemVariant) => void;
  removeItem: (id: string) => void;
  toggleLove: (id: string) => void;
  recordCheck: (c: CheckRecord) => void;
  /** Ribbon = mark a look as a memorable moment (Journal v1). */
  toggleRibbon: (lookId: string) => void;
  recordWear: (itemIds: string[]) => void;
  recordReject: (pairKey: string, itemIds: string[]) => void;
  seedCloset: () => void;
  startFresh: () => void;
}

const EMPTY_PROFILE: Profile = {
  name: "",
  vibes: [],
  modest: false,
  feeling: "confident",
  onboarded: false,
};

export const useLovanya = create<LovanyaState>()(
  persist(
    (set, get) => ({
      profile: EMPTY_PROFILE,
      items: [],
      checks: [],
      bias: {},
      rejectedPairs: [],
      wearCount: 0,
      seeded: false,

      setProfile: (p) => set({ profile: { ...get().profile, ...p } }),

      addItem: (item) => set({ items: [item, ...get().items] }),

      mergeVariant: (canonicalId, variant) =>
        set({
          items: get().items.map((i) => {
            if (i.id !== canonicalId) return i;
            return {
              ...i,
              // Canonical stays canonical; adopt the photo only if it has none.
              photo: i.photo ?? variant.photo,
              variants: [...(i.variants ?? []), variant].slice(-10),
            };
          }),
        }),

      removeItem: (id) =>
        set({ items: get().items.filter((i) => i.id !== id) }),

      toggleLove: (id) => {
        const items = get().items.map((i) =>
          i.id === id ? { ...i, loved: !i.loved } : i
        );
        const item = items.find((i) => i.id === id);
        const bias = { ...get().bias };
        if (item) {
          for (const c of item.colors) {
            const fam = colorFamily(c);
            bias[fam] = (bias[fam] ?? 0) + (item.loved ? 1.5 : -1.5);
          }
        }
        set({ items, bias });
      },

      recordCheck: (c) =>
        set({ checks: [c, ...get().checks].slice(0, 30) }),

      toggleRibbon: (lookId) =>
        set({
          checks: get().checks.map((c) =>
            c.id === lookId ? { ...c, ribboned: !c.ribboned } : c
          ),
        }),

      // Wearing a recommendation teaches Aura what worked.
      recordWear: (itemIds) => {
        const bias = { ...get().bias };
        const items = get().items.map((i) => {
          if (!itemIds.includes(i.id)) return i;
          for (const c of i.colors) {
            const fam = colorFamily(c);
            bias[fam] = (bias[fam] ?? 0) + 0.8;
          }
          return { ...i, timesWorn: i.timesWorn + 1 };
        });
        set({ items, bias, wearCount: get().wearCount + 1 });
      },

      // A pass teaches her what didn't.
      recordReject: (key, itemIds) => {
        const bias = { ...get().bias };
        for (const id of itemIds) {
          const item = get().items.find((i) => i.id === id);
          if (!item) continue;
          for (const c of item.colors) {
            const fam = colorFamily(c);
            bias[fam] = (bias[fam] ?? 0) - 0.25;
          }
        }
        set({
          bias,
          rejectedPairs: [key, ...get().rejectedPairs].slice(0, 20),
        });
      },

      seedCloset: () => set({ items: SEED_ITEMS, seeded: true }),

      startFresh: () =>
        set({
          items: [],
          checks: [],
          bias: {},
          rejectedPairs: [],
          wearCount: 0,
          seeded: true, // don't re-seed after an intentional fresh start
        }),
    }),
    {
      name: "lovanya-v1",
      storage: createJSONStorage(() => localStorage),
    }
  )
);

/** True once the persisted store has loaded on the client. */
export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    if (useLovanya.persist.hasHydrated()) setHydrated(true);
    const unsub = useLovanya.persist.onFinishHydration(() =>
      setHydrated(true)
    );
    return unsub;
  }, []);
  return hydrated;
}

export const uid = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
