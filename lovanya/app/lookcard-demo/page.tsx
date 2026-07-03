"use client";

import { useEffect, useRef, useState } from "react";
import LookCard from "@/components/LookCard";
import { parseLookFile, type LookFile } from "@/lib/garment-json";
import { buildLookCard } from "@/lib/lookcard";

/**
 * LookCard renderer fed from JSON (visual-pipeline-v1 interchange).
 * Loads /fixtures/looks.json by default; "Load JSON" renders any pipeline
 * output file dropped in. Dev page — not linked from the app nav.
 */
export default function LookCardDemo() {
  const [file, setFile] = useState<LookFile | null>(null);
  const [source, setSource] = useState("fixtures/looks.json");
  const [loadError, setLoadError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/fixtures/looks.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!cancelled) setFile(parseLookFile(data));
      })
      .catch((e) => {
        if (!cancelled) setLoadError(`Couldn't load fixtures/looks.json — ${e.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePick: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    f.text()
      .then((text) => {
        setFile(parseLookFile(JSON.parse(text)));
        setSource(f.name);
        setLoadError(null);
      })
      .catch((err) => setLoadError(`${f.name} is not valid JSON — ${err.message}`));
    e.target.value = ""; // allow re-picking the same file
  };

  return (
    <div className="pb-8">
      <h1 className="font-display text-[28px] font-bold text-ink">
        LookCards from JSON
      </h1>
      <p className="mt-1 text-[13px] text-ink-soft">
        Rendering <span className="font-semibold text-ink">{source}</span> — the
        pipeline↔renderer interchange. Garments accept the app shape
        (colors[]) or the pipeline&rsquo;s canonical shape (color_primary).
      </p>

      <button
        onClick={() => inputRef.current?.click()}
        className="mt-3 rounded-full border border-line bg-card px-4 py-2 text-[13px] font-semibold text-rosewood shadow-soft active:scale-95"
      >
        Load a different JSON…
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".json,application/json"
        onChange={handlePick}
        className="hidden"
      />

      {loadError && (
        <p className="mt-4 rounded-2xl border border-line bg-card px-4 py-3 text-[13px] text-red-700">
          {loadError}
        </p>
      )}

      {!file && !loadError && (
        <p className="mt-6 text-[13px] italic text-ink-soft">Loading fixtures…</p>
      )}

      {file && file.errors.length > 0 && (
        <div className="mt-4 rounded-2xl border border-line bg-card px-4 py-3">
          <p className="text-[12px] font-semibold text-ink">
            {file.errors.length} entr{file.errors.length === 1 ? "y" : "ies"} skipped:
          </p>
          <ul className="mt-1 list-inside list-disc text-[11.5px] text-ink-soft">
            {file.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {file && file.outfits.length === 0 && (
        <p className="mt-6 text-[13px] italic text-ink-soft">
          Nothing renderable in this file.
        </p>
      )}

      {file && (
        <div className="mt-6 space-y-7">
          {file.outfits.map((fx) => {
            const card = buildLookCard(fx);
            if (!card) return null;
            // Determinism check (critical rule #2): a second build of the
            // same input must be byte-identical.
            const deterministic =
              JSON.stringify(card) === JSON.stringify(buildLookCard(fx));
            const hero = fx.garments.find((g) => g.id === card.heroGarmentId);
            return (
              <div key={fx.id}>
                <div className="mb-2 flex items-center justify-between text-[11.5px]">
                  <span className="font-semibold uppercase tracking-[1.2px] text-rosewood">
                    {card.layout} · {fx.garments.length}{" "}
                    {fx.garments.length === 1 ? "piece" : "pieces"}
                  </span>
                  <span className={deterministic ? "text-sage" : "text-red-600"}>
                    {deterministic ? "deterministic ✓" : "NON-DETERMINISTIC ✗"}
                  </span>
                </div>
                <LookCard card={card} garments={fx.garments} />
                <p className="mt-1.5 text-[11px] text-ink-faint">
                  hero: {hero?.name ?? card.heroGarmentId}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
