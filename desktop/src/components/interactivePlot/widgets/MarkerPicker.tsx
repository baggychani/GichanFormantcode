import { MARKERS } from "../designDefaults";

export function MarkerPicker({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (marker: string) => void;
  disabled?: boolean;
}) {
  const icon = (marker: string) => {
    const common = { stroke: "currentColor", strokeWidth: 1.6 };
    if (marker === "s" || marker === "ws") {
      return <rect x="7" y="7" width="10" height="10" rx="1" fill={marker === "s" ? "currentColor" : "none"} {...common} />;
    }
    if (marker === "^") return <path d="M12 6 18 17H6Z" fill="currentColor" {...common} />;
    if (marker === "D") return <path d="m12 5 7 7-7 7-7-7Z" fill="currentColor" {...common} />;
    return <circle cx="12" cy="12" r="5.5" fill={marker === "o" ? "currentColor" : "none"} {...common} />;
  };

  return (
    <div className="marker-options">
      {MARKERS.map(([marker]) => (
        <button
          key={marker}
          type="button"
          disabled={disabled}
          className={value === marker ? "is-active" : ""}
          onClick={() => onChange(marker)}
        >
          <svg viewBox="0 0 24 24" aria-hidden>
            {icon(marker)}
          </svg>
        </button>
      ))}
    </div>
  );
}
