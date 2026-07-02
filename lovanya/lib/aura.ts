import type { Profile, Weather } from "./types";

/**
 * Aura's ambient voice for the Today screen — warm, brief, never judgmental.
 * Deterministic per day so she feels consistent, not random.
 */

export function greeting(name: string, date = new Date()): string {
  const h = date.getHours();
  const who = name ? `, ${name}` : "";
  if (h < 5) return `Still up${who}?`;
  if (h < 12) return `Good morning${who}`;
  if (h < 18) return `Good afternoon${who}`;
  return `Good evening${who}`;
}

export function dailyLine(
  profile: Profile,
  weather: Weather,
  stats: { items: number; checks: number; wears: number },
  date = new Date()
): string {
  const seed =
    date.getDate() + date.getMonth() * 31 + (profile.name.length || 1);

  const pool: string[] = [];

  if (stats.checks === 0 && stats.wears === 0) {
    pool.push(
      "I'm here whenever you're unsure. Try an outfit check — it takes seconds.",
      "Your closet is ready. Want me to style something for today?"
    );
  }
  if (weather.tempC >= 24) {
    pool.push(
      "Warm day ahead — your light fabrics are about to shine.",
      "Sunshine kind of day. Soft colors would feel lovely."
    );
  } else if (weather.tempC <= 13) {
    pool.push(
      "A layering day — those are secretly the best outfits.",
      "Cozy weather. Let's make warm look elegant."
    );
  } else {
    pool.push(
      "Mild and easy today — almost anything you love will work.",
      "A gentle day. A gentle look. You've got this."
    );
  }
  if (stats.wears >= 3) {
    pool.push("I'm learning your taste a little more each day. It suits you.");
  }
  if (profile.vibes.length) {
    pool.push(
      `${profile.vibes[0]} is so your lane. Lean into it today.`
    );
  }

  return pool[seed % pool.length];
}

export const THINKING_LINES = [
  "Let me look at you properly…",
  "Reading the colors…",
  "Hmm, this is lovely…",
  "Thinking about your day…",
  "Almost there…",
];

export function fmtDate(date = new Date()): string {
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}
