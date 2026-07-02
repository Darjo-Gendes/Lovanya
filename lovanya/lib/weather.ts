import type { Weather } from "./types";

/**
 * Mocked weather, deterministic per calendar day so the app feels stable
 * across reloads. Swap for a real provider (e.g. Open-Meteo) later without
 * touching any consumer.
 */
export function getTodayWeather(date = new Date()): Weather {
  const seed =
    date.getFullYear() * 372 + (date.getMonth() + 1) * 31 + date.getDate();
  const rand = (n: number) => {
    const x = Math.sin(seed * 97 + n * 13) * 10000;
    return x - Math.floor(x);
  };

  // Season curve for the northern hemisphere; June ≈ warm.
  const month = date.getMonth();
  const seasonal = [8, 9, 13, 17, 22, 26, 29, 28, 24, 18, 12, 9][month];
  const tempC = Math.round(seasonal + (rand(1) - 0.5) * 6);

  const conditions: Weather["condition"][] = [
    "sunny",
    "sunny",
    "cloudy",
    "breezy",
    "rainy",
  ];
  const condition = conditions[Math.floor(rand(2) * conditions.length)];

  const labels: Record<Weather["condition"], string> = {
    sunny: "Sunny",
    cloudy: "Soft clouds",
    breezy: "Light breeze",
    rainy: "Gentle rain",
  };

  let blurb: string;
  if (tempC >= 26) blurb = "A warm one — light fabrics will be your friend.";
  else if (tempC >= 19) blurb = "Mild and lovely. Most of your closet works today.";
  else if (tempC >= 12) blurb = "A touch cool — a soft layer would feel just right.";
  else blurb = "Chilly today. Let's wrap you in something warm.";
  if (condition === "rainy") blurb += " Maybe skip the delicate shoes.";

  return { tempC, condition, label: labels[condition], blurb };
}
