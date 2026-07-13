import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  Table2,
  Tags,
  Upload,
  X,
} from "lucide-react";
import appIconUrl from "../../../assets/icon.ico";
import "./DataGuide.css";

type DataGuideProps = {
  open: boolean;
  onClose: () => void;
};

type ColumnExample = {
  title: string;
  note: string;
  headers: string[];
  rows: string[][];
  showHeader: boolean;
};

const COLUMN_EXAMPLES: ColumnExample[] = [
  {
    title: "F1 · F2 · F3 · 라벨",
    note: "첫 행에 F1, F2 같은 열 이름이 있어도 자동으로 건너뜁니다.",
    headers: ["F1", "F2", "F3", "라벨"],
    rows: [
      ["730", "1090", "2800", "/a/"],
      ["320", "2250", "3100", "/i/"],
      ["350", "950", "870", "/u/"],
      ["480", "1800", "2600", "/e/"],
    ],
    showHeader: true,
  },
  {
    title: "F1 · F2 · 라벨 (F3 없음)",
    note: "F3를 사용하지 않으면 F2 바로 다음 열에 라벨을 두세요.",
    headers: ["F1", "F2", "라벨"],
    rows: [
      ["730", "1090", "/a/"],
      ["320", "2250", "/i/"],
      ["350", "950", "/u/"],
      ["480", "1800", "/e/"],
    ],
    showHeader: true,
  },
  {
    title: "소수점이 포함된 데이터",
    note: "소수점은 계산할 때 자동으로 반올림됩니다. 파일 전체에 같은 형식을 사용하세요.",
    headers: ["F1", "F2", "라벨"],
    rows: [
      ["730.4", "1089.7", "/a/"],
      ["320.2", "2248.5", "/i/"],
      ["350.8", "948.3", "/u/"],
      ["480.1", "1799.6", "/e/"],
    ],
    showHeader: true,
  },
  {
    title: "열 이름이 없는 데이터",
    note: "첫 줄부터 측정값이 시작되어도 정상적으로 읽습니다.",
    headers: ["F1", "F2", "라벨"],
    rows: [
      ["730", "1090", "/a/"],
      ["320", "2250", "/i/"],
      ["350", "950", "/u/"],
      ["480", "1800", "/e/"],
    ],
    showHeader: false,
  },
];

const FORMATS = ["TXT", "CSV", "TSV", "XLS", "XLSX"];

export function DataGuide({ open, onClose }: DataGuideProps) {
  const [exampleIndex, setExampleIndex] = useState(0);
  const example = COLUMN_EXAMPLES[exampleIndex];

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="guide-backdrop" onMouseDown={onClose}>
      <section
        className="guide-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="data-guide-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="guide-header">
          <div className="guide-brand">
            <img src={appIconUrl} alt="" aria-hidden />
            <div>
              <span>GichanFormant</span>
              <strong id="data-guide-title">데이터 파일 준비 가이드</strong>
            </div>
          </div>
          <button
            type="button"
            className="guide-close"
            onClick={onClose}
            aria-label="데이터 가이드 닫기"
          >
            <X size={19} />
          </button>
        </header>

        <div className="guide-layout">
          <nav className="guide-nav" aria-label="가이드 목차">
            <div className="guide-nav-intro">
              <span>파일을 넣기 전에</span>
              <strong>세 가지만 확인하세요.</strong>
              <p>열 순서와 라벨 표기만 맞으면 나머지는 자동으로 처리합니다.</p>
            </div>
            <a href="#guide-files"><span>01</span>지원 파일</a>
            <a href="#guide-columns"><span>02</span>열 구성</a>
            <a href="#guide-labels"><span>03</span>라벨 표기</a>
            <div className="guide-nav-tip">
              <Upload size={17} />
              <span>여러 파일을 한 번에 선택하거나 메인 화면에 끌어놓을 수 있습니다.</span>
            </div>
          </nav>

          <div className="guide-content">
            <section className="guide-section" id="guide-files">
              <div className="guide-section-heading">
                <span className="guide-section-icon"><FileSpreadsheet size={19} /></span>
                <div>
                  <span>01</span>
                  <h2>지원하는 파일</h2>
                </div>
              </div>
              <p className="guide-lead">
                아래 형식은 별도 변환 없이 바로 읽을 수 있습니다. 파일이 아주 많다면 여러 번에
                나눠 불러오는 편이 안정적입니다.
              </p>
              <div className="format-row">
                {FORMATS.map((format) => <span key={format}>{format}</span>)}
              </div>
            </section>

            <section className="guide-section" id="guide-columns">
              <div className="guide-section-heading">
                <span className="guide-section-icon"><Table2 size={19} /></span>
                <div>
                  <span>02</span>
                  <h2>열은 이 순서로 놓습니다</h2>
                </div>
              </div>
              <p className="guide-lead">
                F1과 F2는 필수입니다. F3를 쓰지 않을 때는 빈 열을 만들지 말고 F2 다음에 라벨을
                바로 놓으세요.
              </p>

              <div className="column-map" aria-label="권장 열 순서">
                {[
                  ["A열", "F1", "필수"],
                  ["B열", "F2", "필수"],
                  ["C열", "F3", "선택"],
                  ["마지막 열", "라벨", "필수"],
                ].map(([column, name, requirement]) => (
                  <div key={column}>
                    <span>{column}</span>
                    <strong>{name}</strong>
                    <small>{requirement}</small>
                  </div>
                ))}
              </div>

              <div className="guide-rules">
                <div><Check size={15} /><span>첫 행의 F1, F2 같은 열 이름은 자동으로 건너뜁니다.</span></div>
                <div><Check size={15} /><span>소수점이 있는 값은 계산할 때 자동으로 반올림합니다.</span></div>
                <div><AlertTriangle size={15} /><span>F4 이상은 읽지 않으며, F1이 F2보다 큰 행은 제외합니다.</span></div>
              </div>

              <div className="example-card">
                <div className="example-header">
                  <div>
                    <span>파일 예시</span>
                    <strong>{example.title}</strong>
                    <p>{example.note}</p>
                  </div>
                  <div className="example-nav">
                    <button
                      type="button"
                      onClick={() => setExampleIndex((index) => Math.max(0, index - 1))}
                      disabled={exampleIndex === 0}
                      aria-label="이전 예시"
                    >
                      <ChevronLeft size={17} />
                    </button>
                    <span>{exampleIndex + 1} / {COLUMN_EXAMPLES.length}</span>
                    <button
                      type="button"
                      onClick={() => setExampleIndex((index) => Math.min(COLUMN_EXAMPLES.length - 1, index + 1))}
                      disabled={exampleIndex === COLUMN_EXAMPLES.length - 1}
                      aria-label="다음 예시"
                    >
                      <ChevronRight size={17} />
                    </button>
                  </div>
                </div>
                <div className="example-table-wrap">
                  <table>
                    {example.showHeader ? (
                      <thead><tr>{example.headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
                    ) : null}
                    <tbody>
                      {example.rows.map((row, rowIndex) => (
                        <tr key={`${exampleIndex}-${rowIndex}`}>
                          {row.map((value, cellIndex) => (
                            <td key={`${value}-${cellIndex}`} className={cellIndex === row.length - 1 ? "label-cell" : ""}>
                              {value}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <section className="guide-section" id="guide-labels">
              <div className="guide-section-heading">
                <span className="guide-section-icon"><Tags size={19} /></span>
                <div>
                  <span>03</span>
                  <h2>모음 라벨은 슬래시로 감쌉니다</h2>
                </div>
              </div>
              <p className="guide-lead">
                로마자, 한글, IPA, 장음 기호를 모두 사용할 수 있습니다. 분석할 라벨의 앞뒤에
                슬래시를 붙여 주세요.
              </p>
              <div className="label-examples">
                <div className="is-good">
                  <span><Check size={15} /> 올바른 표기</span>
                  <strong>/a/ · /ㅏ/ · /ʌ/ · /e/ · /aː/</strong>
                </div>
                <div className="is-bad">
                  <span><X size={15} /> 제외되는 표기</span>
                  <strong>a · ㅏ · “e” · [ㅜ]</strong>
                </div>
              </div>
            </section>
          </div>
        </div>

        <footer className="guide-footer">
          <span>준비한 파일은 메인 화면의 데이터 영역에 끌어놓으면 됩니다.</span>
          <button type="button" onClick={onClose}>가이드 닫기</button>
        </footer>
      </section>
    </div>
  );
}
