/** Shared swatch set for design / draw color pickers. */
export const PALETTE_SWATCHES = [
  "#000000",
  "#202938",
  "#606060",
  "#9ca3af",
  "#FF0000",
  "#ef2929",
  "#f97316",
  "#eab308",
  "#16a34a",
  "#0891b2",
  "#2563eb",
  "#7c3aed",
] as const;

export function PalettePicker({
  label,
  value,
  onChange,
  allowTransparent = false,
  disabled = false,
}: {
  label: string;
  value: string | null;
  onChange: (color: string | null) => void;
  allowTransparent?: boolean;
  disabled?: boolean;
}) {
  return (
    <details className="palette-picker">
      <summary aria-disabled={disabled}>
        <span>{label}</span>
        <i className={!value ? "is-transparent" : ""} style={value ? { background: value } : undefined} />
      </summary>
      {!disabled ? (
        <div className="palette-popover">
          {allowTransparent ? (
            <button
              type="button"
              className={`transparent-swatch ${value === null ? "is-selected" : ""}`}
              onClick={(event) => {
                onChange(null);
                event.currentTarget.closest("details")?.removeAttribute("open");
              }}
              aria-label="투명"
            />
          ) : null}
          {PALETTE_SWATCHES.map((color) => (
            <button
              key={color}
              type="button"
              className={value === color ? "is-selected" : ""}
              style={{ background: color }}
              onClick={(event) => {
                onChange(color);
                event.currentTarget.closest("details")?.removeAttribute("open");
              }}
              aria-label={color}
            />
          ))}
        </div>
      ) : null}
    </details>
  );
}
