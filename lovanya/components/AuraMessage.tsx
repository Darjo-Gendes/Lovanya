import AuraOrb from "./AuraOrb";

export default function AuraMessage({
  children,
  label = "Aura",
}: {
  children: React.ReactNode;
  label?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <AuraOrb size={34} />
      <div className="card flex-1 rounded-tl-md px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rosewood">
          {label}
        </p>
        <p className="mt-1 font-display text-[15px] italic leading-snug text-ink">
          {children}
        </p>
      </div>
    </div>
  );
}
