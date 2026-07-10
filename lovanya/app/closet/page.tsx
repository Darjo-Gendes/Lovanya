"use client";

import { useMemo, useState } from "react";
import {
  Add,
  ArrowDown2,
  ArrowRight2,
  Clock,
  Heart,
  InfoCircle,
  More,
  SearchNormal1,
  ShoppingBag,
  SliderHorizontal,
} from "iconsax-react";
import AuraMessage from "@/components/AuraMessage";
import AuraOrb from "@/components/AuraOrb";
import ItemThumb from "@/components/ItemThumb";
import PhotoCapture from "@/components/PhotoCapture";
import Button from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import Sheet from "@/components/ui/Sheet";
import { stylist, type ItemDraft } from "@/lib/ai";
import { findLikelyDuplicate, type DuplicateMatch } from "@/lib/dedup";
import { colorFamily, colorName, downscaleImage, extractPalette } from "@/lib/color";
import { uid, useLovanya } from "@/lib/store";
import { CATEGORIES, type Category, type WardrobeItem } from "@/lib/types";

/* A four-point sparkle, matched to the design. */
function Sparkle({ size = 14, color = "#e8b24a", className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={color}
      className={className}
    >
      <path d="M12 2c.4 4 2 5.6 6 6-4 .4-5.6 2-6 6-.4-4-2-5.6-6-6 4-.4 5.6-2 6-6z" />
    </svg>
  );
}

const SORTS = ["recent", "worn", "name"] as const;
type Sort = (typeof SORTS)[number];
const SORT_LABEL: Record<Sort, string> = {
  recent: "Recently Added",
  worn: "Most Worn",
  name: "A – Z",
};

const catLabel = (c: Category) =>
  CATEGORIES.find((x) => x.id === c)?.label ?? c;

const wornText = (n: number) => (n > 0 ? `Worn ${n}×` : "Not worn yet");

export default function Wardrobe() {
  const items = useLovanya((s) => s.items);
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [filter, setFilter] = useState<Category | "all">("all");
  const [sort, setSort] = useState<Sort>("recent");
  const [adding, setAdding] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = items.filter((i) => {
      if (filter !== "all" && i.category !== filter) return false;
      if (!q) return true;
      return (
        i.name.toLowerCase().includes(q) ||
        i.colors.some((c) => colorName(c).includes(q))
      );
    });
    const arr = filtered.slice();
    if (sort === "worn") arr.sort((a, b) => b.timesWorn - a.timesWorn);
    else if (sort === "name") arr.sort((a, b) => a.name.localeCompare(b.name));
    else arr.sort((a, b) => b.addedAt - a.addedAt);
    return arr;
  }, [items, query, filter, sort]);

  const stats = useMemo(() => {
    if (items.length === 0) return null;
    const byWorn = [...items].sort((a, b) => b.timesWorn - a.timesWorn);
    const mostWorn = byWorn[0];
    const leastUsed = byWorn[byWorn.length - 1];
    const cats = new Set(items.map((i) => i.category)).size;
    const fams = new Set(items.flatMap((i) => i.colors).map(colorFamily)).size;
    const ratio =
      (cats / CATEGORIES.length) * 0.6 + (Math.min(fams, 6) / 6) * 0.4;
    const health =
      ratio >= 0.62
        ? { label: "Well Balanced", note: "Great mix of styles and colors." }
        : ratio >= 0.4
          ? { label: "Coming Together", note: "A few more pieces will round it out." }
          : { label: "Just Getting Started", note: "Add pieces across categories to balance it." };
    return { total: items.length, mostWorn, leastUsed, health };
  }, [items]);

  const cycleSort = () =>
    setSort((s) => SORTS[(SORTS.indexOf(s) + 1) % SORTS.length]);

  const selected = items.find((i) => i.id === selectedId) ?? null;

  return (
    <div>
      {/* ===== Brand + actions ===== */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-start gap-1">
          <span className="font-script text-[32px] leading-none text-rosewood">
            Lovanya
          </span>
          <Sparkle size={14} color="#d56f88" />
        </div>
        <div className="flex gap-2.5">
          <button
            onClick={() => setSearchOpen((v) => !v)}
            aria-label="Search"
            className={`flex h-[42px] w-[42px] items-center justify-center rounded-[13px] shadow-soft transition-colors active:scale-95 ${
              searchOpen ? "bg-rosewood text-white" : "bg-card text-ink-soft"
            }`}
          >
            <SearchNormal1 size={20} />
          </button>
          <button
            onClick={cycleSort}
            aria-label="Change sorting"
            className="flex h-[42px] w-[42px] items-center justify-center rounded-[13px] bg-card text-ink-soft shadow-soft active:scale-95"
          >
            <SliderHorizontal size={20} />
          </button>
        </div>
      </div>

      {searchOpen && (
        <div className="relative mt-4">
          <SearchNormal1
            size={16}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint"
          />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or color…"
            className="w-full rounded-full border border-line bg-card py-3 pl-11 pr-4 text-[14px] placeholder:text-ink-faint focus:border-rosewood"
          />
        </div>
      )}

      {/* ===== Title ===== */}
      <div className="mt-4">
        <h1 className="font-display text-[38px] font-bold leading-none tracking-[-0.5px] text-ink">
          My Wardrobe
        </h1>
        <p className="mt-2 flex items-center gap-1.5 text-[14px] text-ink-soft">
          {items.length} {items.length === 1 ? "piece" : "pieces"} thoughtfully
          collected. <Sparkle size={14} />
        </p>
      </div>

      {items.length === 0 ? (
        <div className="mt-8 space-y-5">
          <AuraMessage>
            Your wardrobe is a blank canvas. Add your first piece — just a quick
            photo, and I&rsquo;ll handle the organizing.
          </AuraMessage>
          <Button full onClick={() => setAdding(true)}>
            <Add size={17} /> Add my first piece
          </Button>
        </div>
      ) : (
        <>
          {/* ===== Stats card ===== */}
          {stats && (
            <div className="mt-5 rounded-[26px] bg-gradient-to-br from-blush to-blush-deep p-5 shadow-soft">
              <div className="flex gap-2.5">
                {/* total */}
                <div className="w-[92px] flex-none">
                  <div className="text-[12.5px] font-medium text-ink-soft">
                    Total Items
                  </div>
                  <div className="mt-2.5 flex items-center gap-2">
                    <span
                      className="flex h-10 w-10 flex-none items-center justify-center rounded-[13px] text-white shadow-lift"
                      style={{ background: "linear-gradient(150deg,#eba7af,#df8b99)" }}
                    >
                      <ShoppingBag size={18} />
                    </span>
                    <div className="min-w-0">
                      <div className="font-display text-[25px] font-bold leading-none text-ink">
                        {stats.total}
                      </div>
                      <div className="mt-0.5 text-[11px] text-ink-soft">
                        Pieces
                      </div>
                    </div>
                  </div>
                </div>

                {/* most worn */}
                <StatPeek
                  label="Most Worn"
                  item={stats.mostWorn}
                  caption={`${stats.mostWorn.timesWorn} ${stats.mostWorn.timesWorn === 1 ? "wear" : "wears"}`}
                />

                {/* least used */}
                <StatPeek
                  label="Least Used"
                  item={stats.leastUsed}
                  caption={`${stats.leastUsed.timesWorn} ${stats.leastUsed.timesWorn === 1 ? "wear" : "wears"}`}
                />
              </div>

              <div className="my-[18px] h-px bg-[rgba(140,90,95,0.16)]" />

              {/* closet health */}
              <div className="flex items-center gap-3.5">
                <span className="flex h-12 w-12 flex-none items-center justify-center rounded-[15px] bg-[#e8f0d8]">
                  <Sparkle size={24} color="#8da767" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium text-ink-soft">
                    Closet Health
                  </div>
                  <div className="font-display text-[18px] font-semibold leading-tight text-ink">
                    {stats.health.label}
                  </div>
                  <div className="mt-0.5 text-[12px] leading-snug text-ink-soft">
                    {stats.health.note}
                  </div>
                </div>
                <ArrowRight2 size={20} className="text-rosewood" />
              </div>
            </div>
          )}

          {/* ===== Organize banner ===== */}
          <button
            onClick={() => setAdding(true)}
            className="mt-4 flex w-full items-center gap-3.5 rounded-[22px] bg-gradient-to-br from-[#de869b] to-[#d06f86] p-[18px] text-left shadow-lift active:scale-[0.99]"
          >
            <span className="flex h-[46px] w-[46px] flex-none items-center justify-center">
              <Hanger />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[17px] font-semibold leading-tight text-white">
                Organize Closet
              </span>
              <span className="mt-1 block text-[12px] leading-snug text-white/85">
                Add items, auto-categorize and tidy your wardrobe.
              </span>
            </span>
            <ArrowRight2 size={20} className="text-white" />
          </button>

          {/* ===== Filter chips ===== */}
          <div className="no-scrollbar -mx-5 mt-[18px] flex gap-2.5 overflow-x-auto px-5 pb-1">
            <Chip selected={filter === "all"} onClick={() => setFilter("all")}>
              All
            </Chip>
            {CATEGORIES.map((c) => (
              <Chip
                key={c.id}
                selected={filter === c.id}
                onClick={() => setFilter(c.id)}
              >
                {c.label}
              </Chip>
            ))}
          </div>

          {/* ===== Your items ===== */}
          <div className="mt-6 flex items-center justify-between">
            <h2 className="text-[19px] font-semibold text-ink">Your Items</h2>
            <button
              onClick={cycleSort}
              className="flex items-center gap-1.5 text-[13px] text-ink-faint active:scale-95"
            >
              {SORT_LABEL[sort]}
              <ArrowDown2 size={14} />
            </button>
          </div>

          <div className="mt-3.5 grid grid-cols-3 gap-[13px]">
            {visible.map((item) => (
              <div key={item.id}>
                <button
                  onClick={() => setSelectedId(item.id)}
                  className="block w-full text-left"
                >
                  <div className="relative overflow-hidden rounded-2xl shadow-soft">
                    <ItemThumb item={item} className="bg-card" rounded="rounded-2xl" />
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedId(item.id);
                      }}
                      className="absolute right-1.5 top-1.5 flex h-[26px] w-[26px] items-center justify-center rounded-full bg-card/95 text-ink-soft shadow-sm"
                    >
                      {item.loved ? (
                        <Heart size={13} className="text-rosewood" fill="currentColor" />
                      ) : (
                        <More size={15} />
                      )}
                    </span>
                  </div>
                  <div className="mt-2 line-clamp-1 text-[12.5px] font-semibold text-ink">
                    {item.name}
                  </div>
                  <div className="mt-0.5 text-[10.5px] text-ink-faint">
                    {catLabel(item.category)}
                  </div>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span
                      className="h-[7px] w-[7px] rounded-full"
                      style={{ background: item.colors[0] ?? "#d8c4bc" }}
                    />
                    <span className="text-[10.5px] text-ink-soft">
                      {wornText(item.timesWorn)}
                    </span>
                  </div>
                </button>
              </div>
            ))}
            {visible.length === 0 && (
              <p className="col-span-3 py-12 text-center text-sm text-ink-soft">
                Nothing matches — yet.
              </p>
            )}
          </div>
        </>
      )}

      <AddItemSheet open={adding} onClose={() => setAdding(false)} />
      <ItemDetailSheet item={selected} onClose={() => setSelectedId(null)} />
    </div>
  );
}

/* ------------------------------------------------------------------ */

function StatPeek({
  label,
  item,
  caption,
}: {
  label: string;
  item: WardrobeItem;
  caption: string;
}) {
  return (
    <div className="min-w-0 flex-1">
      <div className="text-[12.5px] font-medium text-ink-soft">{label}</div>
      <div className="mt-2.5 flex items-start gap-2">
        <ItemThumb
          item={item}
          className="w-[38px] flex-none"
          rounded="rounded-[11px]"
        />
        <div className="min-w-0">
          <div className="line-clamp-2 text-[11.5px] font-semibold leading-tight text-ink">
            {item.name}
          </div>
          <div className="mt-1 text-[10.5px] leading-tight text-ink-soft">
            {caption}
          </div>
        </div>
      </div>
    </div>
  );
}

function Hanger() {
  return (
    <svg
      width="38"
      height="38"
      viewBox="0 0 40 40"
      fill="none"
      stroke="#fff"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 11.5a2.4 2.4 0 1 1 2.4-2.4" />
      <path d="M20 11.5 7.5 21.4c-1 .8-.45 2.4.85 2.4h23.3c1.3 0 1.85-1.6.85-2.4L20 11.5Z" />
      <path d="M30 9.5l1.4-1.4M33 11l1.6-.4M32 14.2l1.6.5" opacity=".9" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */

function AddItemSheet({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const addItem = useLovanya((s) => s.addItem);
  const mergeVariant = useLovanya((s) => s.mergeVariant);
  const items = useLovanya((s) => s.items);
  const [photo, setPhoto] = useState<string | null>(null);
  const [draft, setDraft] = useState<ItemDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [dupe, setDupe] = useState<DuplicateMatch | null>(null);

  const reset = () => {
    setPhoto(null);
    setDraft(null);
    setBusy(false);
    setDupe(null);
  };

  const handleCapture = async (dataUrl: string) => {
    setBusy(true);
    const small = await downscaleImage(dataUrl, 512, 0.72);
    setPhoto(small);
    const palette = await extractPalette(small, 3);
    const d = await stylist.identifyItem({ palette, modestDefault: true });
    setDraft(d);
    setBusy(false);
  };

  const commitNew = () => {
    if (!draft || !photo) return;
    const item: WardrobeItem = {
      id: uid(),
      name: draft.name,
      category: draft.category,
      colors: draft.colors,
      warmth: draft.warmth,
      formality: draft.formality,
      modest: draft.modest,
      photo,
      timesWorn: 0,
      loved: false,
      addedAt: Date.now(),
    };
    addItem(item);
    reset();
    onClose();
  };

  // Dedup gate (visual-pipeline-v1 §4): suggest, never silent-merge.
  const save = () => {
    if (!draft || !photo) return;
    const match = findLikelyDuplicate(draft, items);
    if (match) setDupe(match);
    else commitNew();
  };

  const confirmSame = () => {
    if (!dupe || !photo) return;
    mergeVariant(dupe.item.id, { photo, addedAt: Date.now() });
    reset();
    onClose();
  };

  return (
    <Sheet
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Organize a piece"
    >
      {!photo && !busy && (
        <PhotoCapture
          facing="environment"
          onCapture={handleCapture}
          hint="Lay the piece flat or hang it — good light helps me see its colors."
        />
      )}

      {busy && (
        <div className="flex flex-col items-center py-14 text-center">
          <AuraOrb size={52} />
          <p className="mt-5 font-display text-lg italic text-ink-soft">
            Studying this piece…
          </p>
          <div className="aura-thinking mt-5 h-3 w-48 rounded-full" />
        </div>
      )}

      {photo && dupe && !busy && (
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rosewood">
            Wait — I might know this one
          </p>
          <h3 className="mt-1.5 font-display text-[22px] font-semibold leading-snug text-ink">
            Looks like your {dupe.item.name} — same piece?
          </h3>
          <div className="mt-5 flex items-center justify-center gap-4">
            <div className="text-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo}
                alt="Just captured"
                className="h-28 w-28 rounded-2xl border border-line object-cover shadow-soft"
              />
              <p className="mt-2 text-[11px] text-ink-faint">Just captured</p>
            </div>
            <span className="font-display text-xl text-ink-faint">=?</span>
            <div className="text-center">
              <ItemThumb
                item={dupe.item}
                className="h-28 w-28 shadow-soft"
                rounded="rounded-2xl"
              />
              <p className="mt-2 line-clamp-1 max-w-28 text-[11px] text-ink-faint">
                {dupe.item.name}
              </p>
            </div>
          </div>
          <p className="mt-4 text-center text-[12.5px] text-ink-soft">
            Same category, nearly identical colors. If it&rsquo;s the same
            garment I&rsquo;ll keep one entry and remember this photo.
          </p>
          <div className="mt-6 flex gap-2.5">
            <Button variant="soft" className="flex-1" onClick={commitNew}>
              No, it&rsquo;s new
            </Button>
            <Button className="flex-1" onClick={confirmSame}>
              Same piece
            </Button>
          </div>
        </div>
      )}

      {photo && draft && !busy && !dupe && (
        <div className="space-y-5">
          <div className="flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo}
              alt=""
              className="h-24 w-24 rounded-2xl border border-line object-cover"
            />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rosewood">
                Aura sees
              </p>
              <div className="mt-1.5 flex gap-1.5">
                {draft.colors.map((c, i) => (
                  <span
                    key={i}
                    className="h-6 w-6 rounded-full border-2 border-card shadow-sm"
                    style={{ background: c }}
                  />
                ))}
              </div>
              <p className="mt-1 text-[12.5px] capitalize text-ink-soft">
                {draft.colors.map(colorName).join(" · ")}
              </p>
            </div>
          </div>

          <label className="block">
            <span className="text-[13px] font-semibold text-ink-soft">Name</span>
            <input
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1.5 w-full rounded-2xl border border-line bg-porcelain px-4 py-3 text-[15px]"
            />
          </label>

          <div>
            <p className="text-[13px] font-semibold text-ink-soft">
              Category{" "}
              <span className="font-normal text-ink-faint">
                (my best guess — correct me!)
              </span>
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
                <Chip
                  key={c.id}
                  selected={draft.category === c.id}
                  onClick={() => setDraft({ ...draft, category: c.id })}
                >
                  {c.label}
                </Chip>
              ))}
            </div>
          </div>

          <button
            onClick={() => setDraft({ ...draft, modest: !draft.modest })}
            className="flex w-full items-center justify-between rounded-2xl border border-line bg-porcelain px-5 py-3.5 text-left"
          >
            <span className="text-[14px] font-medium">
              Works for modest styling
            </span>
            <span
              className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
                draft.modest ? "bg-rosewood" : "bg-blush-deep"
              }`}
            >
              <span
                className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${
                  draft.modest ? "left-6" : "left-1"
                }`}
              />
            </span>
          </button>

          <div className="flex gap-2.5">
            <Button variant="soft" className="flex-1" onClick={reset}>
              Retake
            </Button>
            <Button className="flex-1" onClick={save}>
              Add to wardrobe
            </Button>
          </div>
        </div>
      )}
    </Sheet>
  );
}

/* ------------------------------------------------------------------ */

function ItemDetailSheet({
  item,
  onClose,
}: {
  item: WardrobeItem | null;
  onClose: () => void;
}) {
  const toggleLove = useLovanya((s) => s.toggleLove);
  const recordWear = useLovanya((s) => s.recordWear);
  const [added, setAdded] = useState(false);

  const close = () => {
    setAdded(false);
    onClose();
  };

  const addToLook = () => {
    if (!item) return;
    recordWear([item.id]);
    setAdded(true);
    setTimeout(close, 850);
  };

  return (
    <Sheet open={!!item} onClose={close}>
      {item && (
        <div>
          <div className="flex gap-[18px]">
            <ItemThumb
              item={item}
              className="h-[150px] w-[120px] flex-none shadow-soft"
              rounded="rounded-[20px]"
            />
            <div className="flex-1 pt-1">
              <div className="text-[10px] font-semibold uppercase tracking-[1.5px] text-rosewood">
                {catLabel(item.category)}
              </div>
              <div className="mt-1.5 font-display text-[25px] font-semibold leading-tight text-ink">
                {item.name}
              </div>
              <div className="mt-3 flex items-center gap-2 text-[13px] text-ink-soft">
                <Clock size={16} className="text-rosewood/70" />
                {item.timesWorn > 0
                  ? `Worn ${item.timesWorn} ${item.timesWorn === 1 ? "time" : "times"}`
                  : "Not worn yet"}
              </div>
              <div className="mt-1.5 flex items-center gap-2 text-[13px] capitalize text-ink-soft">
                <InfoCircle size={16} className="text-rosewood/70" />
                {item.colors.slice(0, 2).map(colorName).join(" · ")}
                {item.modest ? " · modest" : ""}
              </div>
            </div>
          </div>

          <div className="mt-6 flex gap-2.5">
            <button
              onClick={() => toggleLove(item.id)}
              aria-label={item.loved ? "Loved" : "Love it"}
              className="flex h-[54px] w-[54px] flex-none items-center justify-center rounded-3xl bg-card shadow-soft active:scale-95"
            >
              <Heart
                size={22}
                className="text-rosewood"
                fill={item.loved ? "currentColor" : "none"}
                strokeWidth={1.9}
              />
            </button>
            <button
              onClick={addToLook}
              className="flex h-[54px] flex-1 items-center justify-center gap-2.5 rounded-3xl bg-gradient-to-br from-[#e48ea0] to-[#ce6c84] text-white shadow-lift active:scale-[0.98]"
            >
              <Sparkle size={17} color="#fff" />
              <span className="text-[15px] font-semibold">
                {added ? "Added to today ✓" : "Add to Today's Look"}
              </span>
            </button>
          </div>
          {item.loved && (
            <p className="mt-4 text-center text-[12.5px] italic text-ink-soft">
              Aura will reach for this more often ♡
            </p>
          )}
        </div>
      )}
    </Sheet>
  );
}
