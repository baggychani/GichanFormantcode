/** Statistical p-value display helpers (Pillai and similar tables). */

export function getSignificanceStars(p: number): string {
  if (!Number.isFinite(p)) return "";
  if (p < 0.001) return "***";
  if (p < 0.01) return "**";
  if (p < 0.05) return "*";
  if (p < 0.1) return "†";
  return "";
}

/** Full decimal text for tooltips — no scientific notation (no 2.3e-7). */
export function formatPValueExact(p: number): string {
  if (!Number.isFinite(p)) return "N/A";
  if (p <= 0) return "0";
  if (p >= 0.001) return p.toFixed(3);

  // Enough fractional digits to show the first non-zero digits, capped for readability.
  const digits = Math.min(12, Math.max(6, Math.ceil(-Math.log10(p)) + 2));
  return p.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "");
}

/**
 * Journal-style cell text — never rounds tiny p to "0.0000".
 * - p < 0.001 → "< 0.001 ***"
 * - otherwise → three decimals + stars / †
 * Use `exact` on hover for the full decimal value.
 * `significant` is true when p < 0.05.
 */
export function formatPValue(p: number | null | undefined): {
  text: string;
  exact: string;
  stars: string;
  significant: boolean;
} {
  if (p == null || !Number.isFinite(p)) {
    return { text: "N/A", exact: "N/A", stars: "", significant: false };
  }
  const value = Math.min(1, Math.max(0, p));
  const stars = getSignificanceStars(value);
  const starPart = stars ? ` ${stars}` : "";
  const exact = formatPValueExact(value);
  const significant = value < 0.05;

  if (value < 0.001) {
    return { text: `< 0.001${starPart}`, exact, stars, significant };
  }
  return { text: `${value.toFixed(3)}${starPart}`, exact, stars, significant };
}
