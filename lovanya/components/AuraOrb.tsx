export default function AuraOrb({
  size = 40,
  breathing = true,
}: {
  size?: number;
  breathing?: boolean;
}) {
  return (
    <span
      aria-hidden
      className={`aura-orb inline-block shrink-0 ${breathing ? "animate-breathe" : ""}`}
      style={{ width: size, height: size }}
    />
  );
}
