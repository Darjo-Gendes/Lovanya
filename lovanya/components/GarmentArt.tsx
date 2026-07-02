import { shade } from "@/lib/color";
import type { GarmentKind } from "@/lib/types";

/**
 * Flat, soft garment silhouettes tinted with the item's own palette.
 * Keeps the seeded closet cohesive and premium without stock photos.
 */
export default function GarmentArt({
  kind,
  colors,
  className = "",
}: {
  kind: GarmentKind;
  colors: string[];
  className?: string;
}) {
  const c0 = colors[0] ?? "#d8c4bc";
  const c1 = shade(c0, -18);
  const hi = shade(c0, 26);

  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden>
      {kind === "tee" && (
        <g>
          <path
            d="M37 32 L51 25 Q60 33 69 25 L83 32 Q88 35 90 41 L95 52 Q90 58 82 56 L79 50 L79 91 Q79 97 73 97 L47 97 Q41 97 41 91 L41 50 L38 56 Q30 58 25 52 L30 41 Q32 35 37 32 Z"
            fill={c0}
          />
          <path d="M51 25 Q60 37 69 25" fill="none" stroke={c1} strokeWidth="2.4" strokeLinecap="round" />
        </g>
      )}

      {kind === "blouse" && (
        <g>
          <path
            d="M38 34 L52 26 Q60 33 68 26 L82 34 Q87 37 88 43 L93 54 Q88 60 81 57 L78 51 L80 93 Q70 100 60 100 Q50 100 40 93 L42 51 L39 57 Q32 60 27 54 L32 43 Q33 37 38 34 Z"
            fill={c0}
          />
          <path d="M52 26 L60 40 L68 26" fill="none" stroke={c1} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          {[52, 63, 74, 85].map((y) => (
            <circle key={y} cx="60" cy={y} r="1.7" fill={c1} />
          ))}
        </g>
      )}

      {kind === "knit" && (
        <g>
          <path
            d="M36 34 Q42 27 50 27 Q60 36 70 27 Q78 27 84 34 Q90 40 90 50 L90 77 Q90 83 85 83 L81 80 L81 91 Q81 97 75 97 L45 97 Q39 97 39 91 L39 80 L35 83 Q30 83 30 77 L30 50 Q30 40 36 34 Z"
            fill={c0}
          />
          <path d="M42 90 L78 90" stroke={c1} strokeWidth="1.6" opacity="0.5" />
          <path d="M42 93.5 L78 93.5" stroke={c1} strokeWidth="1.6" opacity="0.5" />
          <path d="M50 27 Q60 35 70 27" fill="none" stroke={c1} strokeWidth="2.4" strokeLinecap="round" />
        </g>
      )}

      {kind === "blazer" && (
        <g>
          <path
            d="M38 30 L54 26 L60 36 L66 26 L82 30 Q88 33 89 40 L92 71 Q92 77 87 77 L82 74 L82 93 Q82 98 77 98 L43 98 Q38 98 38 93 L38 74 L33 77 Q28 77 28 71 L31 40 Q32 33 38 30 Z"
            fill={c0}
          />
          <path d="M54 26 L60 52 L50 38 Z" fill={c1} />
          <path d="M66 26 L60 52 L70 38 Z" fill={c1} />
          <path d="M60 52 L60 98" stroke={c1} strokeWidth="1.6" opacity="0.7" />
          <circle cx="56" cy="64" r="1.8" fill={c1} />
        </g>
      )}

      {kind === "cardigan" && (
        <g>
          <path
            d="M37 33 Q43 27 51 27 L60 38 L69 27 Q77 27 83 33 Q89 39 89 49 L89 76 Q89 82 84 82 L80 79 L80 92 Q80 97 74 97 L46 97 Q40 97 40 92 L40 79 L36 82 Q31 82 31 76 L31 49 Q31 39 37 33 Z"
            fill={c0}
          />
          <path d="M60 38 L60 97" stroke={c1} strokeWidth="2" opacity="0.75" />
          {[56, 68, 80].map((y) => (
            <circle key={y} cx="56.5" cy={y} r="1.6" fill={c1} />
          ))}
        </g>
      )}

      {kind === "coat" && (
        <g>
          <path
            d="M40 27 L55 23 L60 32 L65 23 L80 27 Q86 30 87 37 L90 59 Q90 65 85 64 L82 61 L84 102 Q72 108 60 108 Q48 108 36 102 L38 61 L35 64 Q30 65 30 59 L33 37 Q34 30 40 27 Z"
            fill={c0}
          />
          <rect x="41" y="64" width="38" height="6.5" rx="3" fill={c1} />
          <rect x="55" y="63" width="10" height="8.5" rx="2" fill={hi} opacity="0.9" />
          <path d="M55 23 L60 44 L52 33 Z" fill={c1} />
          <path d="M65 23 L60 44 L68 33 Z" fill={c1} />
        </g>
      )}

      {kind === "dress" && (
        <g>
          <path
            d="M48 25 Q60 35 72 25 L76 38 Q74 48 69 55 L84 97 Q72 106 60 106 Q48 106 36 97 L51 55 Q46 48 44 38 Z"
            fill={c0}
          />
          <path d="M47 57 Q60 63 73 57" fill="none" stroke={c1} strokeWidth="2.2" strokeLinecap="round" />
          <path d="M60 60 L52 92" stroke={c1} strokeWidth="1.4" opacity="0.45" />
        </g>
      )}

      {kind === "slipdress" && (
        <g>
          <path d="M50 20 L52 32" stroke={c1} strokeWidth="2" strokeLinecap="round" />
          <path d="M70 20 L68 32" stroke={c1} strokeWidth="2" strokeLinecap="round" />
          <path
            d="M50 32 Q60 39 70 32 L74 46 L76 99 Q68 105 60 105 Q52 105 44 99 L46 46 Z"
            fill={c0}
          />
          <path d="M50 32 Q60 44 70 32" fill="none" stroke={c1} strokeWidth="1.8" strokeLinecap="round" />
        </g>
      )}

      {kind === "skirt" && (
        <g>
          <rect x="42" y="32" width="36" height="7" rx="3.5" fill={c1} />
          <path
            d="M43 40 L77 40 L88 93 Q74 103 60 103 Q46 103 32 93 Z"
            fill={c0}
          />
          <path d="M52 40 L45 96" stroke={c1} strokeWidth="1.4" opacity="0.5" />
          <path d="M60 40 L60 102" stroke={c1} strokeWidth="1.4" opacity="0.5" />
          <path d="M68 40 L75 96" stroke={c1} strokeWidth="1.4" opacity="0.5" />
        </g>
      )}

      {(kind === "trousers" || kind === "jeans") && (
        <g>
          <rect x="40" y="26" width="40" height="7" rx="3.5" fill={c1} />
          <path d="M41 34 L58.5 34 L56 102 Q47 106 37 102 Z" fill={c0} />
          <path d="M61.5 34 L79 34 L83 102 Q73 106 64 102 Z" fill={c0} />
          {kind === "jeans" && (
            <>
              <path d="M44 40 Q50 46 56 40" fill="none" stroke={c1} strokeWidth="1.4" opacity="0.7" />
              <path d="M64 40 Q70 46 76 40" fill="none" stroke={c1} strokeWidth="1.4" opacity="0.7" />
              <rect x="39" y="94" width="18" height="6" rx="2" fill={hi} opacity="0.55" />
              <rect x="64" y="94" width="18" height="6" rx="2" fill={hi} opacity="0.55" />
            </>
          )}
        </g>
      )}

      {kind === "flats" && (
        <g>
          <path
            d="M24 80 Q26 68 44 66 Q68 62 86 72 Q96 77 96 82 Q96 88 86 88 L30 88 Q22 88 24 80 Z"
            fill={c0}
          />
          <ellipse cx="48" cy="73" rx="15" ry="5.5" fill={hi} opacity="0.8" />
          <circle cx="34" cy="74" r="2.4" fill={c1} />
          <path d="M26 86 L94 86" stroke={c1} strokeWidth="2" opacity="0.6" />
        </g>
      )}

      {kind === "heels" && (
        <g>
          <path
            d="M22 82 Q26 68 42 66 Q64 62 80 70 L88 74 Q94 77 94 82 L94 88 L84 88 L82 76 Q60 70 42 77 L40 88 L26 88 Q21 88 22 82 Z"
            fill={c0}
          />
          <rect x="80" y="76" width="11" height="12" rx="2" fill={c1} />
          <ellipse cx="46" cy="72" rx="13" ry="5" fill={hi} opacity="0.8" />
        </g>
      )}

      {kind === "sneakers" && (
        <g>
          <path
            d="M22 78 Q22 64 36 64 L56 64 Q63 64 68 68 L84 76 Q96 80 96 85 L96 88 Q96 92 88 92 L30 92 Q22 92 22 84 Z"
            fill={c0}
          />
          <rect x="22" y="87" width="74" height="6" rx="3" fill={hi} />
          <path d="M40 66 L46 76 M48 65 L54 74" stroke={c1} strokeWidth="1.8" strokeLinecap="round" opacity="0.7" />
        </g>
      )}

      {kind === "tote" && (
        <g>
          <path d="M45 46 Q45 29 60 29 Q75 29 75 46" fill="none" stroke={c1} strokeWidth="4" strokeLinecap="round" />
          <path d="M32 46 L88 46 L82 97 Q60 102 38 97 Z" fill={c0} />
          <path d="M34 54 L86 54" stroke={c1} strokeWidth="1.6" opacity="0.5" />
        </g>
      )}

      {kind === "crossbody" && (
        <g>
          <path d="M37 54 Q38 18 60 16 Q82 18 83 54" fill="none" stroke={c1} strokeWidth="3" strokeLinecap="round" />
          <rect x="33" y="52" width="54" height="36" rx="11" fill={c0} />
          <path d="M33 64 Q60 72 87 64 L87 60 Q60 50 33 60 Z" fill={c1} opacity="0.85" />
          <circle cx="60" cy="70" r="3" fill={hi} />
        </g>
      )}

      {kind === "scarf" && (
        <g>
          <path
            d="M28 86 Q32 42 58 31 Q84 22 94 33 Q72 36 60 52 Q48 68 46 94 Q36 94 28 86 Z"
            fill={c0}
          />
          <path d="M36 80 Q40 50 60 38" fill="none" stroke={c1} strokeWidth="1.6" opacity="0.5" />
          <path d="M44 95 L42 104 M50 95 L50 104 M56 93 L58 102" stroke={c1} strokeWidth="2" strokeLinecap="round" />
        </g>
      )}
    </svg>
  );
}
