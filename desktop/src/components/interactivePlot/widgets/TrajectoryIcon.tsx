import type { DrawArrowHead, DrawArrowMode } from "../types";

/** PySide create_trajectory_icon 대응 — 화살표 위치/모양 미리보기. */
export function TrajectoryIcon({ mode, head }: { mode: DrawArrowMode; head?: DrawArrowHead }) {
  const headStyle = head ?? "stealth";
  const tips = mode === "end" ? [44] : mode === "all" ? [27, 44] : [];
  const length = 8.5;
  const width = 4.6;
  const cy = 12;
  return (
    <svg className="trajectory-icon" viewBox="0 0 54 24" width="44" height="20" aria-hidden>
      <line x1="10" y1={cy} x2="44" y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      {tips.map((ax) => {
        if (headStyle === "open") {
          return (
            <g key={`open-${ax}`}>
              <line x1={ax - length} y1={cy - width} x2={ax} y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              <line x1={ax - length} y1={cy + width} x2={ax} y2={cy} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
            </g>
          );
        }
        if (headStyle === "latex") {
          return <polygon key={`latex-${ax}`} points={`${ax},${cy} ${ax - length},${cy - width} ${ax - length},${cy + width}`} fill="currentColor" />;
        }
        const indent = 3.6;
        return (
          <polygon
            key={`stealth-${ax}`}
            points={`${ax},${cy} ${ax - length},${cy - width} ${ax - length + indent},${cy} ${ax - length},${cy + width}`}
            fill="currentColor"
          />
        );
      })}
      {[10, 27, 44].map((x) => (
        <circle key={x} cx={x} cy={cy} r="2" fill="currentColor" />
      ))}
    </svg>
  );
}
