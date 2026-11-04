// Drawings made for this project (no external assets). The product icon comes from the data source theme.

/** Frame colour per product type, in the order the data source lists the types (identity, not ranking). */
export const FRAME_COLORS = ["var(--g-frame-1)", "var(--g-frame-2)", "var(--g-frame-3)", "var(--g-frame-4)"];

export function frameColor(index: number): string {
  return FRAME_COLORS[(index < 0 ? 0 : index) % FRAME_COLORS.length];
}

/** A stylised bicycle: dark tyres, a coloured frame, saddle and bars. */
export function Bike({ color = "var(--g-frame-1)", width = 150 }: { color?: string; width?: number }) {
  return (
    <svg className="bike" width={width} height={width * 0.6} viewBox="0 0 150 90" aria-hidden="true">
      <ellipse cx="75" cy="84" rx="64" ry="3.5" className="bike-shadow" />
      {[34, 116].map((cx) => (
        <g key={cx}>
          <circle cx={cx} cy="60" r="23" className="bike-tyre" />
          <circle cx={cx} cy="60" r="17.5" className="bike-rim" />
          <path d={`M${cx - 17} 60 H${cx + 17} M${cx} 43 V77 M${cx - 12} 48 L${cx + 12} 72 M${cx + 12} 48 L${cx - 12} 72`}
            className="bike-spokes" />
          <circle cx={cx} cy="60" r="3" className="bike-hub" />
        </g>
      ))}
      <g stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" fill="none">
        <path d="M34 60 L58 30 L100 30 L72 62 Z" />
        <path d="M58 30 L54 22" />
        <path d="M100 30 L116 60" />
        <path d="M98 24 L102 36" />
      </g>
      <path d="M44 20 Q54 16 64 20" className="bike-saddle" />
      <path d="M92 22 Q100 16 110 20" className="bike-bars" />
      <circle cx="72" cy="62" r="6" className="bike-crank" />
    </svg>
  );
}

export function BicycleIcon({ size = 44 }: { size?: number }) {
  return <Bike width={size} />;
}

export function BoxIcon({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size * 0.62} viewBox="0 0 64 40" fill="none" stroke="currentColor" strokeWidth="2.6"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M18 12 L32 5 L46 12 L46 30 L32 37 L18 30 Z M18 12 L32 19 L46 12 M32 19 L32 37" />
    </svg>
  );
}

export function ProductIcon({ icon, size, color }: { icon: string; size?: number; color?: string }) {
  return icon === "bicycle" ? <Bike width={size} color={color} /> : <BoxIcon size={size} />;
}
