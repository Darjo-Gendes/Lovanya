"use client";

import { type ElementType, useMemo, useState } from "react";
import Link from "next/link";
import { Wine } from "lucide-react";
import {
  Award,
  Bookmark,
  Calendar,
  Camera,
  Category,
  Check,
  ColorSwatch,
  SearchNormal1,
  SliderHorizontal,
} from "iconsax-react";
import ItemThumb from "@/components/ItemThumb";
import Button from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import Meter from "@/components/ui/Meter";
import Sheet from "@/components/ui/Sheet";
import { colorFamily, colorName, shade } from "@/lib/color";
import { useLovanya } from "@/lib/store";
import { OCCASIONS, type Look, type Occasion } from "@/lib/types";

/* ---------------------------------------------------------------- helpers */

const occLabel = (o: Occasion) =>
  OCCASIONS.find((x) => x.id === o)?.label ?? o;

/** Title for a look — user note, else an occasion-derived fallback. */
const lookTitle = (look: Look) =>
  look.title && look.title.trim() ? look.title : `${occLabel(look.occasion)} look`;

/** "{n} garments · {occasion}" — missing parts omitted (mock's meta line). */
function metaLine(look: Look): string {
  const parts: string[] = [];
  const n = look.garmentIds?.length ?? 0;
  if (n > 0) parts.push(`${n} ${n === 1 ? "garment" : "garments"}`);
  parts.push(occLabel(look.occasion));
  return parts.join(" · ");
}

/** "Jul 8" — compact date shown on cards. */
const shortDate = (at: number) =>
  new Date(at).toLocaleDateString("en-US", { month: "short", day: "numeric" });

/** Soft palette gradient used when a look has no photo. */
function paletteGradient(hex?: string): string {
  const c0 = hex ?? "#d8c4bc";
  return `linear-gradient(160deg, ${shade(c0, 86)}, ${shade(c0, 62)})`;
}

const startOfDay = (t: number) => {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
};

/** "Today" / "Yesterday" / "8 Jul 2026". */
function dayLabel(at: number): string {
  const diff = Math.round((startOfDay(Date.now()) - startOfDay(at)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return new Date(at).toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "soft-neutral" -> "soft neutral". */
const famLabel = (f: string) => f.replace(/-/g, " ");

type Mode = "feed" | "library";
type Facet = "occasion" | "colors" | "ribboned" | "all";

/* ------------------------------------------------------------------- page */

export default function Journal() {
  const checks = useLovanya((s) => s.checks);
  const items = useLovanya((s) => s.items);
  const toggleRibbon = useLovanya((s) => s.toggleRibbon);

  const [mode, setMode] = useState<Mode>("feed");
  const [openId, setOpenId] = useState<string | null>(null);

  const openLook = checks.find((c) => c.id === openId) ?? null;

  return (
    <div>
      {/* ===== Header ===== */}
      <div className="flex items-start justify-between gap-3">
        <h1 className="font-display text-[34px] font-bold leading-tight text-ink">
          Journal
        </h1>
        <div className="flex gap-2.5 pt-0.5">
          <button
            onClick={() => setMode("feed")}
            aria-label="Feed"
            className="flex h-[42px] w-[42px] items-center justify-center rounded-[13px] bg-card text-ink-soft shadow-soft active:scale-95"
          >
            <Calendar size={20} />
          </button>
          <button
            onClick={() => setMode("library")}
            aria-label="Library"
            className="flex h-[42px] w-[42px] items-center justify-center rounded-[13px] bg-card text-ink-soft shadow-soft active:scale-95"
          >
            <SliderHorizontal size={20} />
          </button>
        </div>
      </div>
      <p className="mt-1.5 text-[14px] text-ink-soft">
        Your style, your story. Every look you&rsquo;ve loved.
      </p>

      {checks.length === 0 ? (
        /* ===== Empty state (both modes) ===== */
        <div className="card mt-6 px-5 py-7 text-center">
          <p className="text-[13.5px] italic text-ink-soft">
            Your journal starts with one look ♡
          </p>
          <Link
            href="/check"
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-br from-rosewood to-rosewood-deep px-5 py-2.5 text-[14px] font-semibold text-white shadow-lift active:scale-[0.97]"
          >
            <Camera size={16} /> Style me
          </Link>
        </div>
      ) : (
        <>
          {/* ===== Mode tabs ===== */}
          <div className="mt-5 flex gap-6 border-b border-line">
            {(["feed", "library"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`-mb-px border-b-2 pb-2 text-[12px] uppercase tracking-wide transition-colors ${
                  mode === m
                    ? "border-rosewood font-semibold text-ink"
                    : "border-transparent text-ink-faint"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {mode === "feed" ? (
            <Feed checks={checks} onOpen={setOpenId} onToggle={toggleRibbon} />
          ) : (
            <LibraryView
              checks={checks}
              items={items}
              onOpen={setOpenId}
              onToggle={toggleRibbon}
            />
          )}
        </>
      )}

      <LookSheet look={openLook} onClose={() => setOpenId(null)} />
    </div>
  );
}

/* ------------------------------------------------------------- ribbon icon */

function RibbonButton({
  look,
  onToggle,
  size = 18,
  className = "",
}: {
  look: Look;
  onToggle: (id: string) => void;
  size?: number;
  className?: string;
}) {
  const active = !!look.ribboned;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onToggle(look.id);
      }}
      aria-label={active ? "Marked as memorable" : "Mark as memorable"}
      className={`flex items-center justify-center active:scale-95 ${className}`}
    >
      <Bookmark
        size={size}
        variant={active ? "Bold" : "Linear"}
        className={active ? "text-rosewood" : "text-ink-faint"}
      />
    </button>
  );
}

/* --------------------------------------------------------------- feed mode */

const FEED_PAGE = 8;

function Feed({
  checks,
  onOpen,
  onToggle,
}: {
  checks: Look[];
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  const [shown, setShown] = useState(FEED_PAGE);

  const groups = useMemo(() => {
    const out: { label: string; looks: Look[] }[] = [];
    for (const look of checks.slice(0, shown)) {
      const label = dayLabel(look.at);
      const last = out[out.length - 1];
      if (last && last.label === label) last.looks.push(look);
      else out.push({ label, looks: [look] });
    }
    return out;
  }, [checks, shown]);

  const heroId = checks[0]?.id;

  return (
    <div className="mt-5">
      {groups.map((g) => (
        <div key={g.label} className="mt-6 first:mt-0">
          <h2 className="text-[13px] font-semibold text-ink-soft">{g.label}</h2>
          <div className="mt-3 space-y-3">
            {g.looks.map((look) =>
              look.id === heroId ? (
                <HeroCard
                  key={look.id}
                  look={look}
                  onOpen={onOpen}
                  onToggle={onToggle}
                />
              ) : (
                <RowCard
                  key={look.id}
                  look={look}
                  onOpen={onOpen}
                  onToggle={onToggle}
                />
              )
            )}
          </div>
        </div>
      ))}

      {checks.length > shown && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => setShown((s) => s + FEED_PAGE)}
            className="rounded-full border border-line bg-card px-5 py-2.5 text-[13px] font-medium text-ink-soft shadow-soft active:scale-95"
          >
            ↓ Load more
          </button>
        </div>
      )}
    </div>
  );
}

function HeroCard({
  look,
  onOpen,
  onToggle,
}: {
  look: Look;
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  return (
    <div
      onClick={() => onOpen(look.id)}
      className="overflow-hidden rounded-[26px] border border-line bg-card shadow-soft active:scale-[0.99]"
    >
      <div className="relative">
        {look.thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={look.thumb}
            alt=""
            className="aspect-[4/5] w-full object-cover"
          />
        ) : (
          <div
            className="aspect-[4/5] w-full"
            style={{ background: paletteGradient(look.palette[0]) }}
          />
        )}

        {look.ribboned && (
          <span className="absolute left-3 top-3 flex h-7 w-7 items-center justify-center rounded-full bg-rosewood text-white shadow-lift">
            <Bookmark size={14} variant="Bold" />
          </span>
        )}

        <RibbonButton
          look={look}
          onToggle={onToggle}
          className="absolute right-3 top-3 h-9 w-9 rounded-full bg-card/90 shadow-soft"
        />
      </div>

      <div className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="min-w-0 truncate font-display text-[19px] font-semibold leading-tight text-ink">
            {lookTitle(look)}
          </p>
          <p className="shrink-0 text-[11.5px] text-ink-faint">
            {shortDate(look.at)}
          </p>
        </div>
        <p className="mt-1 text-[12px] text-ink-soft">{metaLine(look)}</p>
      </div>
    </div>
  );
}

function RowCard({
  look,
  onOpen,
  onToggle,
}: {
  look: Look;
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  return (
    <div
      onClick={() => onOpen(look.id)}
      className="relative flex gap-3.5 rounded-[20px] border border-line bg-card p-3 shadow-soft active:scale-[0.99]"
    >
      <div
        className="relative h-[110px] w-[88px] flex-none overflow-hidden rounded-[14px]"
        style={{
          background: look.thumb ? undefined : paletteGradient(look.palette[0]),
        }}
      >
        {look.thumb && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={look.thumb}
            alt=""
            className="h-full w-full object-cover"
          />
        )}
      </div>
      <div className="min-w-0 flex-1 pt-1.5">
        <p className="truncate font-display text-[15px] font-semibold text-ink">
          {lookTitle(look)}
        </p>
        <p className="mt-0.5 truncate text-[11.5px] text-ink-soft">
          {metaLine(look)}
        </p>
        <p className="mt-0.5 text-[11px] text-ink-faint">
          {shortDate(look.at)}
        </p>
      </div>
      <RibbonButton
        look={look}
        onToggle={onToggle}
        className="absolute bottom-2.5 right-2.5 h-9 w-9 rounded-full"
      />
    </div>
  );
}

/* ------------------------------------------------------------ library mode */

function LibraryView({
  checks,
  items,
  onOpen,
  onToggle,
}: {
  checks: Look[];
  items: ReturnType<typeof useLovanya.getState>["items"];
  onOpen: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [facet, setFacet] = useState<Facet | null>(null);
  const [pick, setPick] = useState<string | null>(null);

  const q = query.trim().toLowerCase();

  const searchResults = useMemo(() => {
    if (!q) return null;
    return checks.filter((look) => {
      const hay = [
        look.title ?? "",
        occLabel(look.occasion),
        ...look.palette.map(colorName),
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [checks, q]);

  // Occasions present, with counts.
  const occCounts = useMemo(
    () =>
      OCCASIONS.map((o) => ({
        id: o.id,
        label: o.label,
        count: checks.filter((c) => c.occasion === o.id).length,
      })).filter((o) => o.count > 0),
    [checks]
  );

  // Color families present, with the number of looks that contain each.
  const famList = useMemo(() => {
    const map = new Map<string, number>();
    for (const look of checks) {
      for (const fam of new Set(look.palette.map(colorFamily))) {
        map.set(fam, (map.get(fam) ?? 0) + 1);
      }
    }
    return [...map.entries()].map(([fam, count]) => ({ fam, count }));
  }, [checks]);

  const ribbonedCount = checks.filter((c) => c.ribboned).length;

  // Pictorial facets per the mock; icon sits in a tinted square, colored
  // with the tint's deeper tone.
  const facetDefs = (
    [
      { key: "occasion", name: "Occasion", icon: Wine, count: occCounts.length, tint: "#FBE0E2", tone: "#D56F88" },
      { key: "colors", name: "Colors", icon: ColorSwatch, count: famList.length, tint: "#EFE4F1", tone: "#9B6FA3" },
      { key: "ribboned", name: "Ribboned", icon: Award, count: ribbonedCount, tint: "#F4E7D6", tone: "#C79A4A" },
      { key: "all", name: "All Looks", icon: Category, count: checks.length, tint: "#E8F0D8", tone: "#8DA767" },
    ] as {
      key: Facet;
      name: string;
      icon: ElementType;
      count: number;
      tint: string;
      tone: string;
    }[]
  ).filter((f) => f.count > 0);

  const list = useMemo(() => {
    if (facet === "ribboned") return checks.filter((c) => c.ribboned);
    if (facet === "all") return checks;
    if (facet === "occasion")
      return pick ? checks.filter((c) => c.occasion === pick) : checks;
    if (facet === "colors")
      return pick
        ? checks.filter((c) => c.palette.map(colorFamily).includes(pick))
        : checks;
    return [];
  }, [facet, pick, checks]);

  const topWorn = useMemo(
    () =>
      [...items]
        .filter((i) => i.timesWorn > 0)
        .sort((a, b) => b.timesWorn - a.timesWorn)
        .slice(0, 4),
    [items]
  );

  const selectFacet = (f: Facet) => {
    setPick(null);
    setFacet((cur) => (cur === f ? null : f));
  };

  return (
    <div className="mt-5">
      {/* ===== Search ===== */}
      <div className="relative">
        <SearchNormal1
          size={16}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search looks, occasions, colors…"
          className="w-full rounded-full border border-line bg-card py-3 pl-11 pr-4 text-[14px] placeholder:text-ink-faint focus:border-rosewood"
        />
      </div>

      {searchResults ? (
        <div className="mt-4 space-y-3">
          {searchResults.length > 0 ? (
            searchResults.map((look) => (
              <RowCard
                key={look.id}
                look={look}
                onOpen={onOpen}
                onToggle={onToggle}
              />
            ))
          ) : (
            <p className="py-10 text-center text-[13.5px] text-ink-soft">
              Nothing matches — yet.
            </p>
          )}
        </div>
      ) : (
        <>
          {/* ===== Browse by ===== */}
          <h3 className="mt-6 text-[15px] font-semibold text-ink">
            Browse by
          </h3>
          <div className="mt-3 grid grid-cols-3 gap-2.5">
            {facetDefs.map((f) => {
              const Icon = f.icon;
              const active = facet === f.key;
              return (
                <button
                  key={f.key}
                  onClick={() => selectFacet(f.key)}
                  className={`card p-3 text-center transition-shadow active:scale-95 ${
                    active ? "ring-1 ring-rosewood" : ""
                  }`}
                >
                  <span
                    className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl"
                    style={{ background: f.tint, color: f.tone }}
                  >
                    <Icon size={18} />
                  </span>
                  <p className="mt-2 text-[13px] font-semibold text-ink">
                    {f.name}
                  </p>
                  <p className="text-[11px] text-ink-faint">{f.count}</p>
                </button>
              );
            })}
          </div>

          {/* ===== Selected facet: chips + list ===== */}
          {facet && (
            <div className="mt-5">
              {facet === "occasion" && (
                <div className="no-scrollbar -mx-5 flex gap-2.5 overflow-x-auto px-5 pb-1">
                  {occCounts.map((o) => (
                    <Chip
                      key={o.id}
                      selected={pick === o.id}
                      onClick={() =>
                        setPick((p) => (p === o.id ? null : o.id))
                      }
                    >
                      {o.label} ({o.count})
                    </Chip>
                  ))}
                </div>
              )}

              {facet === "colors" && (
                <div className="no-scrollbar -mx-5 flex gap-2.5 overflow-x-auto px-5 pb-1">
                  {famList.map((f) => (
                    <Chip
                      key={f.fam}
                      selected={pick === f.fam}
                      onClick={() =>
                        setPick((p) => (p === f.fam ? null : f.fam))
                      }
                      className="capitalize"
                    >
                      {famLabel(f.fam)} ({f.count})
                    </Chip>
                  ))}
                </div>
              )}

              <div className="mt-3 space-y-3">
                {list.length > 0 ? (
                  list.map((look) => (
                    <RowCard
                      key={look.id}
                      look={look}
                      onOpen={onOpen}
                      onToggle={onToggle}
                    />
                  ))
                ) : (
                  <p className="py-8 text-center text-[13.5px] text-ink-soft">
                    Nothing here yet.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ===== Most Worn ===== */}
          {topWorn.length > 0 && (
            <div className="mt-8">
              <h3 className="text-[15px] font-semibold text-ink">
                Most Worn
              </h3>
              <div className="no-scrollbar -mx-5 mt-3 flex gap-3 overflow-x-auto px-5">
                {topWorn.map((item) => (
                  <div key={item.id} className="w-[72px] flex-none">
                    <ItemThumb
                      item={item}
                      className="w-[72px]"
                      rounded="rounded-2xl"
                    />
                    <p className="mt-1.5 line-clamp-1 text-[11px] font-semibold text-ink">
                      {item.name}
                    </p>
                    <p className="text-[10.5px] text-ink-soft">
                      {item.timesWorn} {item.timesWorn === 1 ? "wear" : "wears"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* --------------------------------------------------------------- look sheet */

function LookSheet({
  look,
  onClose,
}: {
  look: Look | null;
  onClose: () => void;
}) {
  const toggleRibbon = useLovanya((s) => s.toggleRibbon);

  return (
    <Sheet open={!!look} onClose={onClose}>
      {look && (
        <div className="space-y-5">
          {look.thumb && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={look.thumb}
              alt=""
              className="max-h-[260px] w-full rounded-2xl object-cover"
            />
          )}

          <div>
            <h2 className="font-display text-[22px] font-semibold leading-tight text-ink">
              {lookTitle(look)}
            </h2>
            <p className="mt-1 text-[12.5px] text-ink-soft">
              {new Date(look.at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}{" "}
              · {occLabel(look.occasion)}
            </p>
          </div>

          <div className="flex items-center gap-3.5">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-rosewood to-gold font-display text-lg font-bold text-white">
              {look.score}
            </div>
            <p className="text-[15px] font-semibold text-ink">
              {look.headline}
            </p>
          </div>

          {look.palette.length > 0 && (
            <div className="flex gap-1.5">
              {look.palette.map((p, i) => (
                <span
                  key={i}
                  className="h-4 w-4 rounded-full border border-line"
                  style={{ background: p }}
                />
              ))}
            </div>
          )}

          {look.breakdown && look.breakdown.length > 0 && (
            <div className="space-y-3">
              {look.breakdown.map((b, i) => (
                <Meter key={i} label={b.label} value={b.score} note={b.note} />
              ))}
            </div>
          )}

          {look.whatWorks && look.whatWorks.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rosewood">
                What worked
              </p>
              <ul className="mt-2 space-y-1.5">
                {look.whatWorks.map((w, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-[13.5px] text-ink"
                  >
                    <Check
                      size={15}
                      className="mt-0.5 flex-none text-rosewood"
                    />
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {look.gentleThought && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gold">
                A gentle thought
              </p>
              <p className="mt-1.5 text-[13.5px] text-ink">
                {look.gentleThought}
              </p>
            </div>
          )}

          {look.auraNote && (
            <p className="text-[13px] italic text-ink-soft">{look.auraNote}</p>
          )}

          <Button variant="soft" full onClick={() => toggleRibbon(look.id)}>
            <Bookmark
              size={16}
              variant={look.ribboned ? "Bold" : "Linear"}
            />
            {look.ribboned ? "Marked as memorable" : "Mark as memorable"}
          </Button>
        </div>
      )}
    </Sheet>
  );
}
