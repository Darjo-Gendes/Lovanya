"use client";

import { motion } from "motion/react";

export default function Meter({
  label,
  value,
  note,
}: {
  label: string;
  value: number;
  note?: string;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-[13.5px] font-semibold">{label}</p>
        {note && <p className="text-xs text-ink-soft">{note}</p>}
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-blush">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-rosewood to-gold"
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.9, ease: "easeOut", delay: 0.15 }}
        />
      </div>
    </div>
  );
}
