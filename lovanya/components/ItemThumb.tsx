import { shade } from "@/lib/color";
import type { WardrobeItem } from "@/lib/types";
import GarmentArt from "./GarmentArt";

/** Square visual for a wardrobe item: user photo, or tinted illustration. */
export default function ItemThumb({
  item,
  className = "",
  rounded = "rounded-2xl",
  style,
}: {
  item: WardrobeItem;
  className?: string;
  rounded?: string;
  /** Merged last, so callers can override position/aspect (e.g. LookCard layouts). */
  style?: React.CSSProperties;
}) {
  const c0 = item.colors[0] ?? "#d8c4bc";
  return (
    <div
      className={`relative aspect-square overflow-hidden ${rounded} ${className}`}
      style={{
        background: item.photo
          ? undefined
          : `linear-gradient(160deg, ${shade(c0, 86)}, ${shade(c0, 62)})`,
        ...style,
      }}
    >
      {item.photo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.photo}
          alt={item.name}
          className="h-full w-full object-cover"
        />
      ) : item.art ? (
        <GarmentArt kind={item.art} colors={item.colors} className="h-full w-full" />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <span
            className="h-10 w-10 rounded-full"
            style={{ background: c0 }}
          />
        </div>
      )}
    </div>
  );
}
