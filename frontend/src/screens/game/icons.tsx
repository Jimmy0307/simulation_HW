// Small line icons drawn for this project (no external assets). The product icon comes from the data source theme.

export function BicycleIcon({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size * 0.62} viewBox="0 0 64 40" fill="none" stroke="currentColor" strokeWidth="2.6"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="13" cy="27" r="10" />
      <circle cx="51" cy="27" r="10" />
      <path d="M13 27 L24 11 L41 11 L51 27 M24 11 L32 27 L41 11 M32 27 L13 27 M21 6 h7 M41 11 l-2 -6 h6" />
    </svg>
  );
}

export function BoxIcon({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size * 0.62} viewBox="0 0 64 40" fill="none" stroke="currentColor" strokeWidth="2.6"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M18 12 L32 5 L46 12 L46 30 L32 37 L18 30 Z M18 12 L32 19 L46 12 M32 19 L32 37" />
    </svg>
  );
}

export function ProductIcon({ icon, size }: { icon: string; size?: number }) {
  return icon === "bicycle" ? <BicycleIcon size={size} /> : <BoxIcon size={size} />;
}
