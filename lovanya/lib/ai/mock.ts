import {
  colorFamily,
  colorName,
  harmonyScore,
  hexToHsl,
  isNeutral,
} from "@/lib/color";
import type {
  Category,
  OutfitAnalysis,
  Recommendation,
  WardrobeItem,
} from "@/lib/types";
import type { ItemDraft, RecContext, StylistAI } from "./stylist";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const thinking = () => wait(650 + Math.random() * 750);

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

const pick = <T,>(arr: T[], seed: number): T => arr[seed % arr.length];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const clamp = (v: number, lo: number, hi: number) =>
  Math.round(Math.max(lo, Math.min(hi, v)));

/* ------------------------------------------------------------------ */
/* Outfit analysis                                                     */
/* ------------------------------------------------------------------ */

const HEADLINES_HIGH = [
  "This is genuinely lovely on you",
  "You found something special today",
  "Quiet confidence — it's all here",
];
const HEADLINES_MID = [
  "This works — with one soft tweak it sings",
  "A solid look with lovely bones",
  "You're closer than you think",
];

const OCCASION_FORMALITY: Record<string, number> = {
  work: 2.4,
  class: 1.6,
  casual: 1.2,
  date: 2.4,
  event: 2.8,
  errands: 1.1,
};

const analyzeOutfitMock: StylistAI["analyzeOutfit"] = async ({
  palette,
  occasion,
  weather,
  profile,
}) => {
  await thinking();
  const seed = hash(palette.join("") + occasion);
  const names = palette.map(colorName);
  const neutrals = palette.filter(isNeutral);
  const colored = palette.filter((c) => !isNeutral(c));

  const harmony = harmonyScore(palette);

  // Darker, more neutral palettes read more formal.
  const avgL =
    palette.reduce((a, c) => a + hexToHsl(c).l, 0) / Math.max(palette.length, 1);
  const paletteFormality =
    1 + (neutrals.length / Math.max(palette.length, 1)) * 1.2 + (avgL < 45 ? 0.7 : 0);
  const target = OCCASION_FORMALITY[occasion] ?? 1.8;
  const occasionFit = clamp(92 - Math.abs(paletteFormality - target) * 11 + (seed % 7), 62, 95);

  const warmDay = weather.tempC >= 24;
  const coolDay = weather.tempC <= 13;
  const lightPalette = avgL >= 58;
  let comfort = 80;
  if (warmDay && lightPalette) comfort = 90;
  if (warmDay && avgL < 40) comfort = 70;
  if (coolDay && avgL < 50) comfort = 87;
  comfort = clamp(comfort + (seed % 5), 62, 95);

  const cohesion = clamp(
    72 +
      (palette.length >= 2 && palette.length <= 4 ? 10 : 0) +
      Math.min(neutrals.length, 2) * 5 +
      (seed % 6),
    62,
    95
  );

  const score = clamp(
    harmony * 0.38 + occasionFit * 0.24 + comfort * 0.16 + cohesion * 0.22,
    62,
    96
  );

  const whatWorks: string[] = [];
  if (colored.length >= 2) {
    whatWorks.push(
      `The ${colorName(colored[0])} and ${colorName(colored[1])} sit beautifully together — that pairing is doing real work.`
    );
  } else if (colored.length === 1) {
    whatWorks.push(
      `Letting ${colorName(colored[0])} carry the look keeps everything focused and intentional.`
    );
  } else {
    whatWorks.push(
      `A fully neutral palette — ${names.slice(0, 2).join(" and ")} — always reads calm and expensive.`
    );
  }
  if (neutrals.length >= 1 && colored.length >= 1) {
    whatWorks.push(
      `Your ${colorName(neutrals[0])} grounds the color so nothing fights for attention.`
    );
  }
  if (occasionFit >= 80)
    whatWorks.push(`The overall mood fits ${occasionLabel(occasion)} naturally.`);

  // One gentle thought, keyed to the softest dimension — never a verdict.
  const weakest = Math.min(harmony, occasionFit, comfort);
  let gentleThought: string;
  if (weakest === harmony && colored.length >= 2) {
    gentleThought = `If you ever want a softer blend, swapping one piece toward ${pick(["ivory", "taupe", "blush"], seed)} would let the ${colorName(colored[0])} breathe a little more.`;
  } else if (weakest === comfort && warmDay) {
    gentleThought = `It's ${weather.tempC}° today — a lighter layer would keep this look feeling effortless all day.`;
  } else if (weakest === comfort && coolDay) {
    gentleThought = `At ${weather.tempC}°, tossing a warm layer over this keeps the silhouette and adds coziness.`;
  } else if (weakest === occasionFit) {
    gentleThought =
      target >= 2.2
        ? `For ${occasionLabel(occasion)}, one slightly dressier piece — shoes or a structured layer — would lift it perfectly.`
        : `This leans a touch polished for ${occasionLabel(occasion)} — which honestly is never a bad thing.`;
  } else {
    gentleThought = `Honestly? I wouldn't change a thing. Maybe one small accent if you're feeling playful.`;
  }

  const auraNote = pick(
    [
      `You wanted to feel ${profile.feeling} today — this gets you there, ${profile.name}.`,
      `${profile.name}, you wear this like it was made for you.`,
      `Walk out the door, ${profile.name}. You're ready.`,
      `Soft, certain, and very you, ${profile.name}.`,
    ],
    seed
  );

  return {
    score,
    headline: score >= 84 ? pick(HEADLINES_HIGH, seed) : pick(HEADLINES_MID, seed),
    palette,
    paletteNames: names,
    breakdown: [
      { label: "Color harmony", score: harmony, note: harmony >= 82 ? "Beautifully balanced" : "Gentle and workable" },
      { label: "Occasion fit", score: occasionFit, note: occasionFit >= 80 ? "Right at home" : "Close — one tweak" },
      { label: "Weather comfort", score: comfort, note: `${weather.tempC}° · ${weather.label}` },
      { label: "Cohesion", score: cohesion, note: cohesion >= 82 ? "Everything belongs" : "Nearly seamless" },
    ],
    whatWorks: whatWorks.slice(0, 3),
    gentleThought,
    auraNote,
  };
};

function occasionLabel(o: string): string {
  return (
    {
      work: "a work day",
      class: "class",
      casual: "a casual day",
      date: "a date",
      event: "an event",
      errands: "errands",
    }[o] ?? "today"
  );
}

/* ------------------------------------------------------------------ */
/* Item identification                                                 */
/* ------------------------------------------------------------------ */

const CATEGORY_NOUNS: Record<Category, string[]> = {
  top: ["relaxed shirt", "soft blouse", "fine knit", "easy top"],
  bottom: ["wide-leg trousers", "midi skirt", "tailored trousers", "relaxed jeans"],
  dress: ["flowing dress", "wrap dress", "everyday dress"],
  outerwear: ["soft blazer", "cardigan", "light coat"],
  shoes: ["everyday flats", "block heels", "clean sneakers"],
  bag: ["everyday tote", "crossbody"],
  accessory: ["featherweight scarf", "silk scarf"],
};

const identifyItemMock: StylistAI["identifyItem"] = async ({
  palette,
  modestDefault,
}) => {
  await thinking();
  const seed = hash(palette.join("|"));
  // Name from the garment's color, not a pale background that crept in.
  const main = palette.find((c) => !isNeutral(c)) ?? palette[0] ?? "#b8a8b0";
  const { l } = hexToHsl(main);

  // Weighted guess — the user confirms or corrects in one tap.
  const weighted: [Category, number][] = [
    ["top", 30],
    ["bottom", 22],
    ["dress", 12],
    ["outerwear", 12],
    ["shoes", 10],
    ["bag", 8],
    ["accessory", 6],
  ];
  const total = weighted.reduce((a, [, w]) => a + w, 0);
  let roll = seed % total;
  let category: Category = "top";
  for (const [c, w] of weighted) {
    if (roll < w) {
      category = c;
      break;
    }
    roll -= w;
  }

  const noun = pick(CATEGORY_NOUNS[category], seed >> 3);
  return {
    name: `${cap(colorName(main))} ${noun}`,
    category,
    colors: palette.slice(0, 3),
    warmth: (l < 38 ? 2 : 1) as 1 | 2 | 3,
    formality: ((seed >> 5) % 3 === 0 ? 1 : 2) as 1 | 2 | 3,
    modest: modestDefault,
  };
};

/* ------------------------------------------------------------------ */
/* Outfit recommendation                                               */
/* ------------------------------------------------------------------ */

const TITLES = [
  "Soft focus",
  "The quiet classic",
  "Effortless grace",
  "Golden hour",
  "Gentle structure",
  "The easy muse",
  "Warm minimalism",
  "Your kind of polished",
];

const MOOD_FORMALITY_NUDGE: Record<string, number> = {
  confident: 0.3,
  elegant: 0.5,
  chic: 0.4,
  calm: 0,
  comfortable: -0.4,
  playful: -0.2,
};

export function pairKey(items: WardrobeItem[]): string {
  return items
    .filter((i) => ["top", "bottom", "dress"].includes(i.category))
    .map((i) => i.id)
    .sort()
    .join("+");
}

const recommendOutfitsMock: StylistAI["recommendOutfits"] = async ({
  wardrobe,
  context,
}) => {
  await thinking();
  const { occasion, mood, weather, modest, bias, rejectedPairs } = context;

  const usable = wardrobe.filter((i) => !modest || i.modest || i.category === "shoes" || i.category === "bag" || i.category === "accessory");
  const by = (c: Category) => usable.filter((i) => i.category === c);

  const tops = by("top");
  const bottoms = by("bottom");
  const dresses = by("dress");
  const outers = by("outerwear");
  const shoes = by("shoes");
  const bags = by("bag");

  const target =
    (OCCASION_FORMALITY[occasion] ?? 1.8) + (MOOD_FORMALITY_NUDGE[mood] ?? 0);
  const needLayer = weather.tempC <= 18;

  // Candidate cores: every dress, every top×bottom.
  const cores: WardrobeItem[][] = [
    ...dresses.map((d) => [d]),
    ...tops.flatMap((t) => bottoms.map((b) => [t, b])),
  ];

  const biasFor = (items: WardrobeItem[]) => {
    let v = 0;
    for (const it of items)
      for (const c of it.colors) v += bias[colorFamily(c)] ?? 0;
    return Math.max(-10, Math.min(10, v));
  };

  const scored = cores
    .map((core) => {
      let items = [...core];

      // Layer for cool days or dressy occasions.
      if (
        outers.length &&
        (needLayer || (target >= 2.4 && weather.tempC < 24))
      ) {
        const layer = [...outers].sort(
          (a, b) =>
            harmonyScore([...items.flatMap((i) => i.colors), ...a.colors]) -
              harmonyScore([...items.flatMap((i) => i.colors), ...b.colors]) <
            0
              ? 1
              : -1
        )[0];
        if (needLayer || layer.formality >= 2) items.push(layer);
      }

      // Shoes: best harmony + formality match.
      if (shoes.length) {
        const shoe = [...shoes].sort(
          (a, b) =>
            Math.abs(a.formality - target) - Math.abs(b.formality - target) ||
            harmonyScore([...items.flatMap((i) => i.colors), ...b.colors]) -
              harmonyScore([...items.flatMap((i) => i.colors), ...a.colors])
        )[0];
        items.push(shoe);
      }
      if (bags.length && occasion !== "errands") {
        const bag = [...bags].sort(
          (a, b) =>
            harmonyScore([...items.flatMap((i) => i.colors), ...b.colors]) -
            harmonyScore([...items.flatMap((i) => i.colors), ...a.colors])
        )[0];
        items.push(bag);
      }

      const colors = items.flatMap((i) => i.colors.slice(0, 2));
      const harmony = harmonyScore(colors);
      const avgFormality =
        core.reduce((a, i) => a + i.formality, 0) / core.length;
      const formalityFit = 100 - Math.abs(avgFormality - target) * 22;
      const avgWarmth = core.reduce((a, i) => a + i.warmth, 0) / core.length;
      const idealWarmth = weather.tempC >= 24 ? 1 : weather.tempC >= 15 ? 1.6 : 2.4;
      const weatherFit = 100 - Math.abs(avgWarmth - idealWarmth) * 18;
      const freshness =
        100 - Math.min(40, (core.reduce((a, i) => a + i.timesWorn, 0) / core.length) * 9);
      const lovedBonus = items.some((i) => i.loved) ? 6 : 0;
      const prefBias = biasFor(items);
      const rejected = rejectedPairs.includes(pairKey(items)) ? -22 : 0;

      const raw =
        harmony * 0.42 +
        formalityFit * 0.2 +
        weatherFit * 0.14 +
        freshness * 0.12 +
        prefBias * 1.2 +
        lovedBonus +
        rejected +
        (hash(pairKey(items) + occasion) % 5);

      return { items, raw, harmony, prefBias };
    })
    .sort((a, b) => b.raw - a.raw)
    .slice(0, 5);

  return scored.slice(0, 4).map(({ items, raw, harmony, prefBias }, idx) => {
    const seed = hash(pairKey(items) + occasion + idx);
    const core = items.filter((i) =>
      ["top", "bottom", "dress"].includes(i.category)
    );
    const layer = items.find((i) => i.category === "outerwear");
    const colored = items
      .flatMap((i) => ({ hex: i.colors[0], item: i }))
      .filter(({ hex }) => !isNeutral(hex));

    const why: string[] = [];
    if (colored.length >= 2) {
      why.push(
        `${cap(colorName(colored[0].hex))} from your ${shortName(colored[0].item)} against the ${colorName(colored[1].hex)} ${shortName(colored[1].item)} — an easy, balanced pairing.`
      );
    } else if (colored.length === 1) {
      why.push(
        `One note of ${colorName(colored[0].hex)} from your ${shortName(colored[0].item)}, wrapped in calm neutrals — focused and polished.`
      );
    } else {
      why.push(
        `A tonal neutral story — ${items.slice(0, 2).map((i) => colorName(i.colors[0])).join(" and ")} — which always reads quietly luxurious.`
      );
    }
    why.push(
      layer && weather.tempC <= 18
        ? `At ${weather.tempC}° the ${shortName(layer)} keeps you warm without losing the line of the outfit.`
        : weather.tempC >= 24
          ? `Light pieces for a ${weather.tempC}° day — you'll be comfortable from morning to evening.`
          : `Just right for ${weather.tempC}° and ${weather.label.toLowerCase()}.`
    );
    const formalLine =
      (OCCASION_FORMALITY[occasion] ?? 1.8) >= 2.2
        ? `Polished enough for ${occasionLabel(occasion)}, but still unmistakably you.`
        : `Relaxed enough for ${occasionLabel(occasion)} while looking completely put-together.`;
    why.push(formalLine);

    const loved = items.find((i) => i.loved);
    if (loved) {
      why.push(`And it features your beloved ${shortName(loved)} — you always glow in it.`);
    } else if (prefBias > 1.5) {
      why.push(`I leaned into the tones you've been loving lately.`);
    }

    return {
      id: `rec-${seed}`,
      items,
      score: clamp(58 + raw * 0.36, 68, 96),
      title: pick(TITLES, seed),
      why: why.slice(0, 4),
      auraNote: pick(
        [
          `This one feels ${mood} to me — exactly what you asked for.`,
          `Trust me on this one. It's quietly stunning.`,
          `Simple pieces, beautiful sum. That's the secret.`,
          `You could wear this twice this week and no one would mind.`,
        ],
        seed >> 2
      ),
    };
  });
};

function shortName(i: WardrobeItem): string {
  // "Ivory silk blouse" -> "silk blouse"
  const parts = i.name.split(" ");
  return parts.length > 2 ? parts.slice(1).join(" ") : i.name.toLowerCase();
}

/* ------------------------------------------------------------------ */

export const MockStylist: StylistAI = {
  analyzeOutfit: analyzeOutfitMock,
  identifyItem: identifyItemMock,
  recommendOutfits: recommendOutfitsMock,
};
