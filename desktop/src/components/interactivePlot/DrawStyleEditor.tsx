import { useEffect, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { useFocusTrap } from "../../useFocusTrap";
import {
  FONT_FAMILIES,
  FONT_WEIGHT_LABELS,
  FONT_WEIGHTS,
  normalizedFontWeight,
} from "./designDefaults";
import {
  clampDrawLineWidth,
  clampDrawTextFontSize,
  clampDrawTextLineSpacing,
  DRAW_LINE_WIDTH_MAX,
  DRAW_LINE_WIDTH_MIN,
  DRAW_LINE_WIDTH_STEP,
  DRAW_TEXT_LINE_SPACING_MAX,
  DRAW_TEXT_LINE_SPACING_MIN,
  DRAW_TEXT_SIZE_MAX,
  DRAW_TEXT_SIZE_MIN,
} from "./drawDefaults";
import type {
  DesignSettings,
  DrawEditorKind,
  DrawEditorMode,
  LegendDraft,
  LineStyleDraft,
  PolygonStyleDraft,
  ReferenceStyleDraft,
  TextStyleDraft,
} from "./types";
import { PalettePicker, ToggleSwitch, TrajectoryIcon } from "./widgets";

function LineStyleButtons({
  value,
  onChange,
}: {
  value: string;
  onChange: (style: string) => void;
}) {
  return (
    <div className="segmented-row is-cols-4">
      <button type="button" className={value === "-" ? "is-active" : ""} onClick={() => onChange("-")} title="실선">
        <i className="line-style-swatch" />
      </button>
      <button type="button" className={value === "--" ? "is-active" : ""} onClick={() => onChange("--")} title="파선">
        <i className="line-style-swatch is-dashed" />
      </button>
      <button type="button" className={value === ":" ? "is-active" : ""} onClick={() => onChange(":")} title="점선">
        <i className="line-style-swatch is-dotted" />
      </button>
      <button type="button" className={value === "-." ? "is-active" : ""} onClick={() => onChange("-.")} title="일점쇄선">
        <i className="line-style-swatch is-dash-dot" />
      </button>
    </div>
  );
}

export function DrawStyleEditor({
  kind,
  mode,
  lineDraft,
  onLineDraftChange,
  polygonDraft,
  onPolygonDraftChange,
  referenceDraft,
  onReferenceDraftChange,
  textDraft,
  onTextDraftChange,
  legendDraft,
  onLegendDraftChange,
  onClose,
  onSave,
}: {
  kind: DrawEditorKind;
  mode: DrawEditorMode;
  lineDraft: LineStyleDraft | null;
  onLineDraftChange: Dispatch<SetStateAction<LineStyleDraft | null>>;
  polygonDraft: PolygonStyleDraft | null;
  onPolygonDraftChange: Dispatch<SetStateAction<PolygonStyleDraft | null>>;
  referenceDraft: ReferenceStyleDraft | null;
  onReferenceDraftChange: Dispatch<SetStateAction<ReferenceStyleDraft | null>>;
  textDraft: TextStyleDraft | null;
  onTextDraftChange: Dispatch<SetStateAction<TextStyleDraft | null>>;
  legendDraft: LegendDraft | null;
  onLegendDraftChange: Dispatch<SetStateAction<LegendDraft | null>>;
  onClose: () => void;
  onSave: () => void;
}) {
  const dialogRef = useRef<HTMLElement | null>(null);
  useFocusTrap(true, dialogRef);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Enter" && event.key !== "Return") return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("textarea, select, [contenteditable='true']")) return;
      event.preventDefault();
      event.stopPropagation();
      onSave();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [onClose, onSave]);

  const title =
    kind === "line"
      ? "선 수정"
      : kind === "polygon"
        ? "영역 수정"
        : kind === "reference"
          ? "기준선 수정"
          : kind === "text"
            ? "텍스트 수정"
            : "범례 수정";

  return (
    <div className="legend-editor-backdrop" role="presentation">
      <section
        ref={dialogRef}
        className="legend-editor-dialog draw-style-editor-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="draw-editor-title"
      >
        <header>
          <div>
            <span className="section-eyebrow">DRAW STYLE</span>
            <h2 id="draw-editor-title">{title}</h2>
            {mode === "layer" && kind !== "legend" ? <p>선택한 레이어에 적용</p> : null}
          </div>
          <button type="button" onClick={onClose} aria-label="닫기">
            <X size={18} />
          </button>
        </header>
        <div className="legend-editor-body">
          {kind === "line" && lineDraft ? (
            <div className="legend-editor-section is-first">
              <div className="legend-editor-section-heading">
                <strong>선 스타일</strong>
              </div>
              <div className="palette-picker-row">
                <PalettePicker
                  label="선 색상"
                  value={lineDraft.line_color}
                  onChange={(line_color) => line_color && onLineDraftChange({ ...lineDraft, line_color })}
                />
              </div>
              <label className="opacity-control">
                <span>
                  선 두께 <b>{clampDrawLineWidth(lineDraft.line_width)}pt</b>
                </span>
                <input
                  type="range"
                  min={DRAW_LINE_WIDTH_MIN}
                  max={DRAW_LINE_WIDTH_MAX}
                  step={DRAW_LINE_WIDTH_STEP}
                  value={clampDrawLineWidth(lineDraft.line_width)}
                  onChange={(event) =>
                    onLineDraftChange({
                      ...lineDraft,
                      line_width: clampDrawLineWidth(Number(event.target.value)),
                    })
                  }
                />
              </label>
              <div className="drawing-style-group">
                <span className="drawing-style-caption">선 스타일</span>
                <LineStyleButtons
                  value={lineDraft.line_style}
                  onChange={(line_style) => onLineDraftChange({ ...lineDraft, line_style })}
                />
              </div>
              <div className="drawing-style-group">
                <span className="drawing-style-caption">화살표 위치</span>
                <div className="segmented-row is-cols-3">
                  <button
                    type="button"
                    className={lineDraft.arrow_mode === "none" ? "is-active" : ""}
                    onClick={() => onLineDraftChange({ ...lineDraft, arrow_mode: "none" })}
                    title="화살표 없음"
                  >
                    <TrajectoryIcon mode="none" />
                  </button>
                  <button
                    type="button"
                    className={lineDraft.arrow_mode === "end" ? "is-active" : ""}
                    onClick={() => onLineDraftChange({ ...lineDraft, arrow_mode: "end" })}
                    title="끝점"
                  >
                    <TrajectoryIcon mode="end" head={lineDraft.arrow_head} />
                  </button>
                  <button
                    type="button"
                    className={lineDraft.arrow_mode === "all" ? "is-active" : ""}
                    onClick={() => onLineDraftChange({ ...lineDraft, arrow_mode: "all" })}
                    title="점마다"
                  >
                    <TrajectoryIcon mode="all" head={lineDraft.arrow_head} />
                  </button>
                </div>
              </div>
              {lineDraft.arrow_mode !== "none" ? (
                <div className="drawing-style-group">
                  <span className="drawing-style-caption">화살표 모양</span>
                  <div className="segmented-row is-cols-3">
                    <button
                      type="button"
                      className={lineDraft.arrow_head === "stealth" ? "is-active" : ""}
                      onClick={() => onLineDraftChange({ ...lineDraft, arrow_head: "stealth" })}
                      title="stealth"
                    >
                      <TrajectoryIcon mode="end" head="stealth" />
                    </button>
                    <button
                      type="button"
                      className={lineDraft.arrow_head === "open" ? "is-active" : ""}
                      onClick={() => onLineDraftChange({ ...lineDraft, arrow_head: "open" })}
                      title="open"
                    >
                      <TrajectoryIcon mode="end" head="open" />
                    </button>
                    <button
                      type="button"
                      className={lineDraft.arrow_head === "latex" ? "is-active" : ""}
                      onClick={() => onLineDraftChange({ ...lineDraft, arrow_head: "latex" })}
                      title="latex"
                    >
                      <TrajectoryIcon mode="end" head="latex" />
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {kind === "polygon" && polygonDraft ? (
            <div className="legend-editor-section is-first">
              <div className="legend-editor-section-heading">
                <strong>영역 스타일</strong>
              </div>
              <div className="drawing-style-group">
                <span className="drawing-style-caption">테두리 스타일</span>
                <LineStyleButtons
                  value={polygonDraft.border_style}
                  onChange={(border_style) => onPolygonDraftChange({ ...polygonDraft, border_style })}
                />
              </div>
              <div className="palette-picker-row">
                <PalettePicker
                  label="테두리 색상"
                  value={polygonDraft.border_color}
                  onChange={(border_color) =>
                    border_color && onPolygonDraftChange({ ...polygonDraft, border_color })
                  }
                />
                <PalettePicker
                  label="채우기 색상"
                  value={polygonDraft.fill_color}
                  onChange={(fill_color) => onPolygonDraftChange({ ...polygonDraft, fill_color })}
                  allowTransparent
                />
              </div>
              <label className="opacity-control">
                <span>
                  채우기 불투명도 <b>{Math.round(polygonDraft.fill_opacity * 100)}%</b>
                </span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={Math.round(polygonDraft.fill_opacity * 100)}
                  onChange={(event) =>
                    onPolygonDraftChange({
                      ...polygonDraft,
                      fill_opacity: Number(event.target.value) / 100,
                    })
                  }
                />
              </label>
            </div>
          ) : null}

          {kind === "reference" && referenceDraft ? (
            <div className="legend-editor-section is-first">
              <div className="legend-editor-section-heading">
                <strong>기준선</strong>
              </div>
              {referenceDraft.valueLabel ? (
                <div className="drawing-tool-summary">
                  <span>값</span>
                  <b>{referenceDraft.valueLabel}</b>
                </div>
              ) : null}
              <div className="reference-mode-row">
                <span>종류</span>
                <div className="segmented-row is-cols-2 reference-mode-choices">
                  <button
                    type="button"
                    className={referenceDraft.mode === "horizontal" ? "is-active" : ""}
                    onClick={() => onReferenceDraftChange({ ...referenceDraft, mode: "horizontal" })}
                  >
                    수평
                  </button>
                  <button
                    type="button"
                    className={referenceDraft.mode === "vertical" ? "is-active" : ""}
                    onClick={() => onReferenceDraftChange({ ...referenceDraft, mode: "vertical" })}
                  >
                    수직
                  </button>
                </div>
              </div>
              <div className="drawing-style-group">
                <span className="drawing-style-caption">선 스타일</span>
                <LineStyleButtons
                  value={referenceDraft.line_style}
                  onChange={(line_style) => onReferenceDraftChange({ ...referenceDraft, line_style })}
                />
              </div>
              <div className="palette-picker-row">
                <PalettePicker
                  label="선 색상"
                  value={referenceDraft.line_color}
                  onChange={(line_color) => onReferenceDraftChange({ ...referenceDraft, line_color })}
                  allowTransparent
                />
              </div>
            </div>
          ) : null}

          {kind === "text" && textDraft ? (
            <div className="legend-editor-section is-first">
              <div className="legend-editor-section-heading">
                <strong>텍스트 스타일</strong>
              </div>
              {mode === "layer" ? (
                <label className="draw-text-content-field">
                  <span>내용 (Enter로 줄바꿈)</span>
                  <textarea
                    value={textDraft.text}
                    onChange={(event) => onTextDraftChange({ ...textDraft, text: event.target.value })}
                    rows={5}
                  />
                </label>
              ) : null}
              <div className="legend-editor-grid">
                <label>
                  <span>글꼴</span>
                  <select
                    value={textDraft.font_family}
                    onChange={(event) => {
                      const font_family = event.target.value;
                      onTextDraftChange({
                        ...textDraft,
                        font_family,
                        font_weight: normalizedFontWeight(font_family, textDraft.font_weight),
                      });
                    }}
                  >
                    {FONT_FAMILIES.map((family) => (
                      <option key={family}>{family}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>굵기</span>
                  <select
                    value={normalizedFontWeight(textDraft.font_family, textDraft.font_weight)}
                    onChange={(event) =>
                      onTextDraftChange({
                        ...textDraft,
                        font_weight: event.target.value as DesignSettings["font_weight"],
                      })
                    }
                    disabled={(FONT_WEIGHTS[textDraft.font_family] ?? []).length <= 1}
                  >
                    {(FONT_WEIGHTS[textDraft.font_family] ?? ["regular"]).map((weight) => (
                      <option key={weight} value={weight}>
                        {FONT_WEIGHT_LABELS[weight]}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="opacity-control">
                <span>
                  글자 크기 <b>{clampDrawTextFontSize(textDraft.font_size)}pt</b>
                </span>
                <input
                  type="range"
                  min={DRAW_TEXT_SIZE_MIN}
                  max={DRAW_TEXT_SIZE_MAX}
                  step={1}
                  value={clampDrawTextFontSize(textDraft.font_size)}
                  onChange={(event) =>
                    onTextDraftChange({
                      ...textDraft,
                      font_size: clampDrawTextFontSize(Number(event.target.value)),
                    })
                  }
                />
              </label>
              <label className="opacity-control">
                <span>
                  줄간격 <b>{clampDrawTextLineSpacing(textDraft.line_spacing).toFixed(2)}</b>
                </span>
                <input
                  type="range"
                  min={DRAW_TEXT_LINE_SPACING_MIN}
                  max={DRAW_TEXT_LINE_SPACING_MAX}
                  step={0.05}
                  value={clampDrawTextLineSpacing(textDraft.line_spacing)}
                  onChange={(event) =>
                    onTextDraftChange({
                      ...textDraft,
                      line_spacing: clampDrawTextLineSpacing(Number(event.target.value)),
                    })
                  }
                />
              </label>
              <ToggleSwitch
                label="기울임"
                checked={textDraft.font_italic}
                onChange={() => onTextDraftChange({ ...textDraft, font_italic: !textDraft.font_italic })}
              />
              <div className="palette-picker-row">
                <PalettePicker
                  label="글자 색상"
                  value={textDraft.text_color}
                  onChange={(text_color) => text_color && onTextDraftChange({ ...textDraft, text_color })}
                />
              </div>
            </div>
          ) : null}

          {kind === "legend" && legendDraft ? (
            <>
              <div className="legend-editor-section is-first">
                <div className="legend-editor-section-heading">
                  <strong>항목 순서와 이름</strong>
                  <button
                    type="button"
                    onClick={() =>
                      onLegendDraftChange({
                        ...legendDraft,
                        entries: [...legendDraft.entries, { series_id: legendDraft.entries.length, text: "새 항목" }],
                      })
                    }
                  >
                    항목 추가
                  </button>
                </div>
                <div className="legend-entry-editor">
                  {legendDraft.entries.map((entry, index) => (
                    <div className="legend-entry-row" key={`${entry.series_id}-${index}`}>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <input
                        value={entry.text}
                        onChange={(event) =>
                          onLegendDraftChange({
                            ...legendDraft,
                            entries: legendDraft.entries.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, text: event.target.value } : item,
                            ),
                          })
                        }
                      />
                      <button
                        type="button"
                        onClick={() =>
                          onLegendDraftChange({
                            ...legendDraft,
                            entries: legendDraft.entries.map((item, itemIndex) =>
                              itemIndex === index && itemIndex > 0
                                ? legendDraft.entries[itemIndex - 1]
                                : itemIndex === index - 1
                                  ? entry
                                  : item,
                            ),
                          })
                        }
                        disabled={index === 0}
                        aria-label="위로 이동"
                        title="위로 이동"
                      >
                        <ArrowUp size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          onLegendDraftChange({
                            ...legendDraft,
                            entries: legendDraft.entries.map((item, itemIndex) =>
                              itemIndex === index && itemIndex < legendDraft.entries.length - 1
                                ? legendDraft.entries[itemIndex + 1]
                                : itemIndex === index + 1
                                  ? entry
                                  : item,
                            ),
                          })
                        }
                        disabled={index === legendDraft.entries.length - 1}
                        aria-label="아래로 이동"
                        title="아래로 이동"
                      >
                        <ArrowDown size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          onLegendDraftChange({
                            ...legendDraft,
                            entries: legendDraft.entries.filter((_, itemIndex) => itemIndex !== index),
                          })
                        }
                        disabled={legendDraft.entries.length <= 1}
                        aria-label="항목 삭제"
                        title="항목 삭제"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
              <div className="legend-editor-section">
                <div className="legend-editor-section-heading">
                  <strong>문자 스타일</strong>
                </div>
                <div className="legend-editor-grid">
                  <label>
                    <span>글꼴</span>
                    <select
                      value={legendDraft.font_family}
                      onChange={(event) =>
                        onLegendDraftChange({ ...legendDraft, font_family: event.target.value })
                      }
                    >
                      {FONT_FAMILIES.map((family) => (
                        <option key={family}>{family}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>굵기</span>
                    <select
                      value={legendDraft.font_weight}
                      onChange={(event) =>
                        onLegendDraftChange({
                          ...legendDraft,
                          font_weight: event.target.value as LegendDraft["font_weight"],
                        })
                      }
                    >
                      <option value="regular">보통</option>
                      <option value="medium">중간</option>
                      <option value="semibold">세미볼드</option>
                      <option value="bold">굵게</option>
                    </select>
                  </label>
                </div>
                <label className="opacity-control legend-size-control">
                  <span>
                    글자 크기 <b>{legendDraft.font_size}pt</b>
                  </span>
                  <input
                    type="range"
                    min="6"
                    max="20"
                    step="1"
                    value={legendDraft.font_size}
                    onChange={(event) =>
                      onLegendDraftChange({ ...legendDraft, font_size: Number(event.target.value) })
                    }
                  />
                </label>
                <ToggleSwitch
                  label="기울임"
                  checked={legendDraft.font_italic}
                  onChange={() =>
                    onLegendDraftChange({ ...legendDraft, font_italic: !legendDraft.font_italic })
                  }
                />
              </div>
              <div className="legend-editor-section">
                <div className="legend-editor-section-heading">
                  <strong>상자 스타일</strong>
                </div>
                <div className="legend-border-toggle-row">
                  <ToggleSwitch
                    label="테두리 표시"
                    checked={legendDraft.show_border}
                    onChange={() =>
                      onLegendDraftChange({ ...legendDraft, show_border: !legendDraft.show_border })
                    }
                  />
                </div>
                <div className="drawing-style-group legend-border-style-group">
                  <span className="drawing-style-caption">테두리 스타일</span>
                  <div className="segmented-row">
                    <button
                      type="button"
                      className={legendDraft.border_style === "-" ? "is-active" : ""}
                      onClick={() => onLegendDraftChange({ ...legendDraft, border_style: "-" })}
                      aria-label="실선"
                      title="실선"
                    >
                      <i className="line-style-swatch" />
                    </button>
                    <button
                      type="button"
                      className={legendDraft.border_style === "--" ? "is-active" : ""}
                      onClick={() => onLegendDraftChange({ ...legendDraft, border_style: "--" })}
                      aria-label="파선"
                      title="파선"
                    >
                      <i className="line-style-swatch is-dashed" />
                    </button>
                    <button
                      type="button"
                      className={legendDraft.border_style === ":" ? "is-active" : ""}
                      onClick={() => onLegendDraftChange({ ...legendDraft, border_style: ":" })}
                      aria-label="점선"
                      title="점선"
                    >
                      <i className="line-style-swatch is-dotted" />
                    </button>
                    <button
                      type="button"
                      className={legendDraft.border_style === "-." ? "is-active" : ""}
                      onClick={() => onLegendDraftChange({ ...legendDraft, border_style: "-." })}
                      aria-label="일점쇄선"
                      title="일점쇄선"
                    >
                      <i className="line-style-swatch is-dash-dot" />
                    </button>
                  </div>
                </div>
                <div className="palette-picker-row">
                  <PalettePicker
                    label="테두리 색상"
                    value={legendDraft.border_color}
                    onChange={(border_color) =>
                      border_color && onLegendDraftChange({ ...legendDraft, border_color })
                    }
                  />
                  <PalettePicker
                    label="채우기 색상"
                    value={legendDraft.fill_color}
                    onChange={(fill_color) =>
                      fill_color && onLegendDraftChange({ ...legendDraft, fill_color })
                    }
                  />
                </div>
                <ToggleSwitch
                  label="배경 채우기"
                  checked={legendDraft.show_fill}
                  onChange={() =>
                    onLegendDraftChange({ ...legendDraft, show_fill: !legendDraft.show_fill })
                  }
                />
                <label className="opacity-control">
                  <span>
                    배경 불투명도 <b>{Math.round(legendDraft.fill_opacity * 100)}%</b>
                  </span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(legendDraft.fill_opacity * 100)}
                    onChange={(event) =>
                      onLegendDraftChange({
                        ...legendDraft,
                        fill_opacity: Number(event.target.value) / 100,
                      })
                    }
                  />
                </label>
              </div>
            </>
          ) : null}
        </div>
        <footer>
          <button type="button" className="wide-action" onClick={onClose}>
            취소
          </button>
          <button type="button" className="wide-action primary" onClick={onSave}>
            적용
          </button>
        </footer>
      </section>
    </div>
  );
}
