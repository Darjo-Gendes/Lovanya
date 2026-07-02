"use client";

export default function Chip({
  selected,
  className = "",
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      className={`shrink-0 rounded-full border px-4 py-2 text-[13.5px] font-medium transition-all active:scale-95 ${
        selected
          ? "border-rosewood bg-rosewood text-white shadow-lift"
          : "border-line bg-card text-ink-soft"
      } ${className}`}
    >
      {children}
    </button>
  );
}
