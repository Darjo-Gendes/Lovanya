"use client";

import { motion } from "motion/react";
import { X } from "lucide-react";

/**
 * Bottom sheet. Renders only while open and unmounts immediately on close —
 * we deliberately avoid AnimatePresence exit animations, which don't complete
 * reliably with React 19 here. Entrance animation is kept.
 */
export default function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  if (!open) return null;

  return (
    <>
      <motion.div
        className="fixed inset-0 z-40 bg-ink/35 backdrop-blur-[2px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={onClose}
      />
      <motion.div
        className="fixed inset-x-0 bottom-0 z-50 mx-auto max-h-[90dvh] w-full max-w-[430px] overflow-y-auto rounded-t-[2rem] border-t border-line bg-card px-6 pb-10 pt-3"
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        transition={{ type: "spring", damping: 32, stiffness: 320 }}
      >
        <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-line" />
        <div className="mb-4 flex items-center justify-between">
          {title ? (
            <h2 className="font-display text-xl">{title}</h2>
          ) : (
            <span />
          )}
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-blush text-rosewood-deep active:scale-95"
          >
            <X size={17} />
          </button>
        </div>
        {children}
      </motion.div>
    </>
  );
}
