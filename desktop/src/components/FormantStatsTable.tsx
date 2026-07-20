import { useCallback, useMemo, useState } from "react";
import { sortVowels } from "../vowelSort";

type FormantStat = {
  x_mean: number;
  x_std: number;
  x_min: number;
  x_max: number;
  y_mean: number;
  y_std: number;
  y_min: number;
  y_max: number;
  count: number;
};

type FormantStatsTableProps = {
  statistics: Record<string, FormantStat>;
  centroidDistances: Record<string, { distance_to_centroid: number }>;
  xLabel: string;
  yLabel: string;
  unitSuffix: string;
};

type CellKey = string;

const CENTROID_DISTANCE_HELP =
  "이 모음의 평균 위치가, 모든 모음 평균으로 만든 공간 중심에서 얼마나 떨어져 있는지를 나타냅니다.";

function fmt1(value: number): string {
  return value.toFixed(1);
}

function fmtRange(min: number, max: number): string {
  return `${fmt1(min)} - ${fmt1(max)}`;
}

export function FormantStatsTable({
  statistics,
  centroidDistances,
  xLabel,
  yLabel,
  unitSuffix,
}: FormantStatsTableProps) {
  const [selected, setSelected] = useState<CellKey | null>(null);

  const selectCell = useCallback((key: CellKey) => {
    setSelected(key);
  }, []);

  const cellClass = (key: CellKey) =>
    `analysis-stat-cell${selected === key ? " is-selected" : ""}`;

  const rows = useMemo(
    () => sortVowels(Object.keys(statistics)).map((vowel) => [vowel, statistics[vowel]] as const),
    [statistics],
  );

  return (
    <div className="analysis-formant-wrap">
      <div className="analysis-formant-scroll">
        <table className="analysis-stats-table analysis-formant-table">
          <colgroup>
            <col className="col-vowel" />
            <col className="col-mean" />
            <col className="col-range" />
            <col className="col-mean" />
            <col className="col-range" />
            <col className="col-distance" />
            <col className="col-n" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">모음</th>
              <th scope="col">{yLabel} 평균 ± SD{unitSuffix}</th>
              <th scope="col">{yLabel} 범위{unitSuffix}</th>
              <th scope="col">{xLabel} 평균 ± SD{unitSuffix}</th>
              <th scope="col">{xLabel} 범위{unitSuffix}</th>
              <th scope="col" title={CENTROID_DISTANCE_HELP}>
                중심 거리{unitSuffix}
              </th>
              <th scope="col" title="해당 모음에 포함된 토큰 개수">
                n
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([vowel, stat]) => {
              const distance = centroidDistances[vowel]?.distance_to_centroid ?? 0;
              const cells: Array<{ key: CellKey; value: string; className?: string; title?: string }> = [
                { key: `${vowel}:vowel`, value: vowel, className: "is-vowel" },
                { key: `${vowel}:y-mean`, value: `${fmt1(stat.y_mean)} ± ${fmt1(stat.y_std)}` },
                { key: `${vowel}:y-range`, value: fmtRange(stat.y_min, stat.y_max) },
                { key: `${vowel}:x-mean`, value: `${fmt1(stat.x_mean)} ± ${fmt1(stat.x_std)}` },
                { key: `${vowel}:x-range`, value: fmtRange(stat.x_min, stat.x_max) },
                {
                  key: `${vowel}:dist`,
                  value: fmt1(distance),
                  title: CENTROID_DISTANCE_HELP,
                },
                { key: `${vowel}:n`, value: String(stat.count), className: "is-n" },
              ];
              return (
                <tr key={vowel}>
                  {cells.map((cell, index) => {
                    const Tag = index === 0 ? "th" : "td";
                    return (
                      <Tag
                        key={cell.key}
                        scope={index === 0 ? "row" : undefined}
                        className={`${cellClass(cell.key)}${cell.className ? ` ${cell.className}` : ""}`}
                        title={cell.title}
                        tabIndex={0}
                        onClick={() => selectCell(cell.key)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectCell(cell.key);
                          }
                        }}
                      >
                        {cell.value}
                      </Tag>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
