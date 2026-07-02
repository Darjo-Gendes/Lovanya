"use client";

const styles = {
  primary:
    "bg-gradient-to-br from-rosewood to-rosewood-deep text-white shadow-lift",
  soft: "bg-blush text-rosewood-deep",
  ghost: "border border-line bg-card/60 text-ink",
} as const;

export default function Button({
  variant = "primary",
  full,
  className = "",
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof styles;
  full?: boolean;
}) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-[15px] font-semibold transition-all active:scale-[0.97] disabled:opacity-50 ${styles[variant]} ${full ? "w-full" : ""} ${className}`}
    >
      {children}
    </button>
  );
}
