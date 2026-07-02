/**
 * Loványa color engine.
 *
 * Real, client-side color intelligence: palette extraction from photos via
 * canvas sampling, fashion-friendly color naming, and harmony scoring based
 * on actual hue relationships. This is what makes the (mock) AI feel honest —
 * the colors it talks about are really in the photo.
 */

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

export function rgbToHex(r: number, g: number, b: number): string {
  const c = (v: number) =>
    Math.max(0, Math.min(255, Math.round(v)))
      .toString(16)
      .padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

/** h: 0–360, s: 0–100, l: 0–100 */
export function rgbToHsl(
  r: number,
  g: number,
  b: number
): { h: number; s: number; l: number } {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) * 60;
    else if (max === g) h = ((b - r) / d + 2) * 60;
    else h = ((r - g) / d + 4) * 60;
  }
  return { h, s: s * 100, l: l * 100 };
}

export function hexToHsl(hex: string) {
  const [r, g, b] = hexToRgb(hex);
  return rgbToHsl(r, g, b);
}

/** Lighten (positive) or darken (negative) a hex color by a percentage. */
export function shade(hex: string, amt: number): string {
  const [r, g, b] = hexToRgb(hex);
  const f = (v: number) =>
    amt >= 0 ? v + (255 - v) * (amt / 100) : v * (1 + amt / 100);
  return rgbToHex(f(r), f(g), f(b));
}

/** Fashion-friendly color name. */
export function colorName(hex: string): string {
  const { h, s, l } = hexToHsl(hex);

  if (l >= 96) return "white";
  if (l >= 88 && s < 22) return "ivory";
  if (l <= 12) return "noir";
  if (s < 9) {
    if (l >= 72) return "dove gray";
    if (l >= 45) return "stone";
    return "charcoal";
  }
  if (s < 22) {
    if (h >= 60 && h < 170) return l >= 58 ? "sage" : "moss";
    if (l >= 70) return h >= 20 && h < 60 ? "cream" : "mist gray";
    if (l >= 42) {
      if (h >= 20 && h < 60) return "taupe";
      if (h >= 170 && h < 280) return "slate";
      return "heather";
    }
    return h >= 180 && h < 290 ? "ink blue" : "espresso";
  }

  if (h < 14 || h >= 345) {
    if (l >= 78) return "blush";
    if (l >= 55) return "dusty rose";
    if (s >= 65 && l >= 38) return "scarlet";
    return "rosewood";
  }
  if (h < 38) {
    if (l >= 78) return h < 26 ? "shell pink" : "champagne";
    if (l >= 50) return "terracotta";
    if (l >= 34) return "rust";
    return "chestnut";
  }
  if (h < 52) {
    if (l >= 75) return "champagne";
    if (l >= 50) return "camel";
    return "bronze";
  }
  if (h < 68) {
    if (l >= 72) return "butter";
    return "gold";
  }
  if (h < 96) {
    if (l >= 70) return "pistachio";
    if (l >= 42) return "olive";
    return "forest";
  }
  if (h < 150) {
    if (l >= 72) return "mint";
    if (l >= 45) return "sage";
    return "emerald";
  }
  if (h < 200) {
    if (l >= 70) return "seafoam";
    return "teal";
  }
  if (h < 230) {
    if (l >= 76) return "sky";
    if (l >= 50) return "denim blue";
    return "navy";
  }
  if (h < 262) {
    if (l >= 74) return "periwinkle";
    if (l >= 42) return "indigo";
    return "midnight";
  }
  if (h < 296) {
    if (l >= 76) return "lavender";
    if (l >= 45) return "violet";
    return "plum";
  }
  if (l >= 76) return "rose";
  if (l >= 48) return "mauve";
  return "berry";
}

/** Coarse family used for preference memory. */
export function colorFamily(hex: string): string {
  const { h, s, l } = hexToHsl(hex);
  if (s < 14) return l >= 60 ? "soft-neutral" : "deep-neutral";
  if (s < 26) return "warm-neutral";
  if (h < 14 || h >= 330) return "rose";
  if (h < 52) return "earth";
  if (h < 68) return "gold";
  if (h < 165) return "green";
  if (h < 262) return "blue";
  return "plum";
}

export function isNeutral(hex: string): boolean {
  const { s, l } = hexToHsl(hex);
  return s < 18 || l > 88 || l < 14;
}

/**
 * Score how well a set of colors sits together (0–100).
 * Analogous and complementary hues score high; mid-distance saturated
 * clashes score lower; neutrals always help ground a palette.
 */
export function harmonyScore(hexes: string[]): number {
  const colored = hexes.filter((c) => !isNeutral(c));
  const neutrals = hexes.length - colored.length;

  if (colored.length <= 1) {
    // Tonal / neutral looks are quietly excellent.
    return 84 + Math.min(neutrals, 3) * 3;
  }

  const hues = colored.map((c) => hexToHsl(c).h);
  let total = 0;
  let pairs = 0;
  for (let i = 0; i < hues.length; i++) {
    for (let j = i + 1; j < hues.length; j++) {
      let d = Math.abs(hues[i] - hues[j]);
      if (d > 180) d = 360 - d;
      let pair: number;
      if (d <= 35) pair = 92; // analogous
      else if (d <= 70) pair = 78;
      else if (d <= 110) pair = 64; // awkward middle
      else if (d <= 145) pair = 72;
      else pair = 86; // complementary
      total += pair;
      pairs++;
    }
  }
  let score = total / pairs;
  score += Math.min(neutrals, 2) * 4; // neutrals ground the look
  return Math.round(Math.max(55, Math.min(96, score)));
}

/**
 * Extract a dominant palette from an image data-URL.
 * Downscales to a small canvas, buckets pixels in quantized RGB space,
 * and returns up to `count` representative hex colors.
 */
export function extractPalette(
  dataUrl: string,
  count = 4
): Promise<string[]> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const size = 56;
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(["#b8a8b0"]);
      ctx.drawImage(img, 0, 0, size, size);
      const { data } = ctx.getImageData(0, 0, size, size);

      const buckets = new Map<
        string,
        { r: number; g: number; b: number; n: number }
      >();
      const Q = 28;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] < 200) continue;
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const key = `${Math.round(r / Q)},${Math.round(g / Q)},${Math.round(b / Q)}`;
        const e = buckets.get(key);
        if (e) {
          e.r += r;
          e.g += g;
          e.b += b;
          e.n++;
        } else {
          buckets.set(key, { r, g, b, n: 1 });
        }
      }

      let entries = [...buckets.values()]
        .map((e) => ({
          hex: rgbToHex(e.r / e.n, e.g / e.n, e.b / e.n),
          n: e.n,
        }))
        .sort((a, b) => b.n - a.n);

      // Drop blown-out background whites unless that's all there is.
      const nonWhite = entries.filter((e) => hexToHsl(e.hex).l < 94);
      if (nonWhite.length >= 2) entries = nonWhite;

      // Merge near-duplicates, keep distinct tones.
      const picked: string[] = [];
      for (const e of entries) {
        const [r1, g1, b1] = hexToRgb(e.hex);
        const distinct = picked.every((p) => {
          const [r2, g2, b2] = hexToRgb(p);
          return (
            Math.abs(r1 - r2) + Math.abs(g1 - g2) + Math.abs(b1 - b2) > 90
          );
        });
        if (distinct) picked.push(e.hex);
        if (picked.length >= count) break;
      }
      resolve(picked.length ? picked : [entries[0]?.hex ?? "#b8a8b0"]);
    };
    img.onerror = () => resolve(["#b8a8b0"]);
    img.src = dataUrl;
  });
}

/** Downscale an image data-URL to keep localStorage light. */
export function downscaleImage(
  dataUrl: string,
  maxDim = 512,
  quality = 0.72
): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
      const w = Math.round(img.width * scale);
      const h = Math.round(img.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(dataUrl);
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}
