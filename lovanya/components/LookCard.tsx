import ItemThumb from "./ItemThumb";
import { shade } from "@/lib/color";
import type { LookCard as LookCardData } from "@/lib/lookcard";
import type { WardrobeItem } from "@/lib/types";

/**
 * Deterministic LookCard renderer — pipeline/docs/visual-pipeline-v1.md §8.
 * A pure function of (card, garments): fixed offsets, fixed rotations, no
 * randomness. The design language mirrors the share/snap card in
 * public/prototype/lovanya-app.html (critical rule #8).
 *
 * Garments are composed via ItemThumb, so photoless items degrade to their
 * tinted illustration or swatch automatically.
 */
export default function LookCard({
  card,
  garments,
  className = "",
}: {
  card: LookCardData;
  /** The wardrobe items referenced by card.garmentIds (missing ids are skipped). */
  garments: WardrobeItem[];
  className?: string;
}) {
  const byId = new Map(garments.map((g) => [g.id, g]));
  const ordered = card.garmentIds
    .map((id) => byId.get(id))
    .filter((g): g is WardrobeItem => Boolean(g));
  const hero = byId.get(card.heroGarmentId) ?? ordered[0];
  const rest = ordered.filter((g) => g !== hero);

  const bg = `linear-gradient(150deg, ${shade(card.palette[0] ?? "#d8c4bc", 88)}, ${shade(
    card.palette[1] ?? card.palette[0] ?? "#d8c4bc",
    68
  )})`;

  return (
    <div
      aria-label={`Look card: ${card.title}`}
      className={`overflow-hidden rounded-[26px] border border-line bg-card shadow-soft ${className}`}
    >
      {/* header */}
      <div className="flex items-center justify-between px-5 pt-4">
        <span className="font-script text-[21px] leading-none text-rosewood">
          Lovanya
        </span>
        <span className="text-[9px] font-semibold uppercase tracking-[1.4px] text-ink-faint">
          Style Snapshot
        </span>
      </div>
      <div className="px-5 pt-1">
        <h3 className="font-display text-[18px] font-semibold text-ink">
          {card.title}
        </h3>
        <p className="mt-0.5 text-[11px] text-ink-faint">{card.subtitle}</p>
      </div>

      {/* visual area */}
      <div
        className="relative mx-5 mt-3.5 aspect-[4/3.4] overflow-hidden rounded-[18px]"
        style={{ background: bg }}
      >
        {!hero ? (
          <div className="flex h-full items-center justify-center">
            <span
              className="h-12 w-12 rounded-full opacity-70"
              style={{ background: card.palette[0] ?? "#d8c4bc" }}
            />
          </div>
        ) : card.layout === "center" ? (
          <ItemThumb
            item={hero}
            rounded="rounded-2xl"
            className="absolute left-1/2 top-1/2 w-[56%] -translate-x-1/2 -translate-y-1/2 shadow-soft"
          />
        ) : card.layout === "diagonal" ? (
          <>
            <ItemThumb
              item={hero}
              rounded="rounded-2xl"
              className="absolute left-[6%] top-[6%] w-[54%] -rotate-2 shadow-soft"
            />
            {rest[0] && (
              <ItemThumb
                item={rest[0]}
                rounded="rounded-2xl"
                className="absolute bottom-[6%] right-[6%] w-[42%] rotate-2 shadow-soft"
              />
            )}
          </>
        ) : card.layout === "stack" ? (
          <>
            <ItemThumb
              item={hero}
              rounded="rounded-2xl"
              className="absolute left-[5%] top-1/2 w-[52%] -translate-y-1/2 shadow-soft"
            />
            {rest.slice(0, 3).map((g, i) => (
              <ItemThumb
                key={g.id}
                item={g}
                rounded="rounded-xl"
                className="absolute shadow-soft"
                // fixed ladder: each secondary steps down the right side
                style={{
                  right: "5%",
                  top: `${8 + i * 30}%`,
                  width: "34%",
                }}
              />
            ))}
          </>
        ) : (
          /* grid: hero spans 2×2, up to 5 secondaries fill the rest */
          <div className="grid h-full grid-cols-3 grid-rows-3 gap-1.5 p-1.5">
            <ItemThumb
              item={hero}
              rounded="rounded-xl"
              className="col-span-2 row-span-2 h-full w-full"
              style={{ aspectRatio: "auto" }}
            />
            {rest.slice(0, 5).map((g) => (
              <ItemThumb
                key={g.id}
                item={g}
                rounded="rounded-xl"
                className="h-full w-full"
                style={{ aspectRatio: "auto" }}
              />
            ))}
          </div>
        )}
      </div>

      {/* footer */}
      <div className="flex items-center gap-2 px-5 pb-4 pt-3">
        <div className="flex gap-1">
          {card.palette.slice(0, 4).map((c, i) => (
            <span
              key={i}
              className="h-3.5 w-3.5 rounded-full border border-line"
              style={{ background: c }}
            />
          ))}
        </div>
        <p className="min-w-0 flex-1 truncate text-right text-[11px] text-ink-soft">
          {card.caption}
        </p>
      </div>
    </div>
  );
}
