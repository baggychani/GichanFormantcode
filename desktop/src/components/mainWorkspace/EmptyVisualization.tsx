export function EmptyVisualization() {
  return (
    <div className="empty-visual" aria-hidden>
      <div className="empty-orbit orbit-a" />
      <div className="empty-orbit orbit-b" />
      <svg viewBox="0 0 620 360" className="formant-ghost">
        <defs>
          <linearGradient id="trace" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#77f2d2" stopOpacity="0.15" />
            <stop offset="0.48" stopColor="#74d8ff" stopOpacity="0.9" />
            <stop offset="1" stopColor="#8c8cff" stopOpacity="0.25" />
          </linearGradient>
        </defs>
        <path
          d="M95 93 C 170 55, 260 77, 302 142 S 420 290, 535 225"
          fill="none"
          stroke="url(#trace)"
          strokeWidth="2"
          strokeDasharray="5 8"
        />
        <path
          d="M112 255 C 215 305, 325 248, 351 185 S 438 82, 526 111"
          fill="none"
          stroke="url(#trace)"
          strokeWidth="1.5"
          opacity="0.62"
        />
        {[
          [111, 99, 7],
          [177, 82, 4],
          [244, 105, 5],
          [302, 151, 8],
          [351, 187, 5],
          [410, 250, 6],
          [475, 260, 4],
          [535, 226, 8],
          [114, 256, 5],
          [212, 280, 7],
          [302, 248, 4],
          [394, 126, 6],
          [465, 96, 4],
          [526, 111, 7],
        ].map(([cx, cy, radius], index) => (
          <g key={`${cx}-${cy}`}>
            <circle
              cx={cx}
              cy={cy}
              r={radius + 7}
              fill="#74d8ff"
              opacity={index % 3 === 0 ? 0.08 : 0.035}
            />
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill={index % 2 === 0 ? "#77f2d2" : "#74d8ff"}
              opacity={index % 3 === 0 ? 0.9 : 0.58}
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
