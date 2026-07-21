import type { VowelAnalysisPage } from "./types";

export function AnalysisFigure({ page }: { page: VowelAnalysisPage }) {
  return (
    <div className={`analysis-figure analysis-figure-${page}`} aria-label={`${page} 분석 시각화`}>
      <svg viewBox="0 0 320 220" role="img">
        <path className="figure-axis figure-axis-x" d="M35 186H285" />
        <path className="figure-axis figure-axis-y" d="M35 186V28" />
        {page === "formant" ? (
          <>
            <ellipse className="figure-ellipse ellipse-a" cx="91" cy="82" rx="35" ry="51" />
            <ellipse className="figure-ellipse ellipse-b" cx="205" cy="104" rx="57" ry="35" />
            <g className="figure-cloud cloud-a">
              {[[80, 72], [91, 81], [99, 93], [87, 101], [104, 78], [73, 91]].map(([cx, cy]) => (
                <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" />
              ))}
            </g>
            <g className="figure-cloud cloud-b">
              {[[176, 100], [193, 111], [205, 98], [217, 91], [229, 108], [211, 119]].map(([cx, cy]) => (
                <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" />
              ))}
            </g>
            <circle className="figure-centroid centroid-a" cx="91" cy="85" r="6" />
            <circle className="figure-centroid centroid-b" cx="205" cy="104" r="6" />
            <text x="80" y="55">i</text>
            <text x="218" y="82">a</text>
          </>
        ) : page === "distance" ? (
          <>
            <ellipse className="figure-ellipse ellipse-a" cx="88" cy="78" rx="34" ry="42" />
            <ellipse className="figure-ellipse ellipse-b" cx="228" cy="138" rx="40" ry="34" />
            <g className="figure-cloud cloud-a">
              {[[78, 68], [90, 76], [98, 88], [84, 92], [100, 72]].map(([cx, cy]) => (
                <circle key={`da-${cx}-${cy}`} cx={cx} cy={cy} r="2.5" />
              ))}
            </g>
            <g className="figure-cloud cloud-b">
              {[[214, 128], [230, 136], [242, 146], [220, 148], [238, 124]].map(([cx, cy]) => (
                <circle key={`db-${cx}-${cy}`} cx={cx} cy={cy} r="2.5" />
              ))}
            </g>
            <path className="figure-distance-line" d="M88 78L228 138" />
            <circle className="figure-centroid centroid-a" cx="88" cy="78" r="6" />
            <circle className="figure-centroid centroid-b" cx="228" cy="138" r="6" />
            <text x="74" y="58">a</text>
            <text x="236" y="158">u</text>
            <text x="138" y="100">d(a, u)</text>
          </>
        ) : (
          <>
            <g className="pillai-group pillai-group-a">
              <circle cx="73" cy="85" r="5" />
              <circle cx="89" cy="98" r="5" />
              <circle cx="80" cy="112" r="5" />
              <circle cx="101" cy="88" r="5" />
            </g>
            <g className="pillai-group pillai-group-b">
              <circle cx="214" cy="77" r="5" />
              <circle cx="232" cy="91" r="5" />
              <circle cx="222" cy="109" r="5" />
              <circle cx="245" cy="83" r="5" />
            </g>
            <path className="pillai-separation" d="M137 48V164" />
            <text x="61" y="54">/i, e/</text>
            <text x="211" y="54">/a, u/</text>
            <text x="143" y="38">Pillai</text>
          </>
        )}
        <text className="figure-axis-label" x="276" y="204">F2</text>
        <text className="figure-axis-label" x="14" y="34">F1</text>
      </svg>
      <span className="figure-caption">
        {page === "formant"
          ? "모음별 중심점과 분포"
          : page === "distance"
            ? "중심점 사이의 실제 거리"
            : "모음 조합 사이의 분리"}
      </span>
    </div>
  );
}
