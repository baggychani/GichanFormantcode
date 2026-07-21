import { Bold, ChevronDown, Italic, Lock, RefreshCcw, Unlock } from "lucide-react";
import {
  FONT_FAMILIES,
  FONT_WEIGHT_LABELS,
  FONT_WEIGHTS,
  fontFamilyStyle,
  normalizedFontWeight,
} from "./designDefaults";
import type { DesignSettings } from "./types";
import { MarkerPicker, PalettePicker, ToggleSwitch } from "./widgets";

export function GlobalDesignPanel({
  design,
  onUpdateDesign,
  onReset,
  globalDesignLocked,
  onToggleLock,
}: {
  design: DesignSettings;
  onUpdateDesign: (patch: Partial<DesignSettings>) => void;
  onReset: () => void;
  globalDesignLocked: boolean;
  onToggleLock: () => void;
}) {
  return (
    <>
      <fieldset className="global-design-form">
        <section className="control-section">
          <div className="section-heading">
            <div>
              <span>01</span>
              <strong>모음 라벨</strong>
            </div>
            <small>전체 레이어</small>
          </div>
          <div className="palette-picker-row">
            <PalettePicker
              label="라벨 색상"
              value={design.lbl_color}
              onChange={(lbl_color) => lbl_color && onUpdateDesign({ lbl_color })}
            />
          </div>
          <div className="text-style-block">
            <span className="control-label">텍스트 설정</span>
            <div className="text-style-row">
              <div className="font-controls font-family-row">
                <select
                  value={design.font_family}
                  onChange={(event) => {
                    const font_family = event.target.value;
                    onUpdateDesign({
                      font_family,
                      font_style: fontFamilyStyle(font_family),
                      font_weight: normalizedFontWeight(font_family, design.font_weight),
                    });
                  }}
                  aria-label="글꼴"
                >
                  {FONT_FAMILIES.map((family) => (
                    <option key={family}>{family}</option>
                  ))}
                </select>
                <select
                  value={normalizedFontWeight(design.font_family, design.font_weight)}
                  onChange={(event) =>
                    onUpdateDesign({
                      font_weight: event.target.value as DesignSettings["font_weight"],
                      lbl_bold: event.target.value === "bold",
                    })
                  }
                  disabled={(FONT_WEIGHTS[design.font_family] ?? []).length <= 1}
                  aria-label="Weight"
                >
                  {(FONT_WEIGHTS[design.font_family] ?? ["regular"]).map((weight) => (
                    <option key={weight} value={weight}>
                      {FONT_WEIGHT_LABELS[weight]}
                    </option>
                  ))}
                </select>
              </div>
              <div className="font-size-row">
                <label className="font-size-control">
                  <span className="font-control-caption">
                    크기 <b>{design.lbl_size}pt</b>
                  </span>
                  <input
                    type="range"
                    min="12"
                    max="28"
                    step="1"
                    value={design.lbl_size}
                    onChange={(event) => onUpdateDesign({ lbl_size: Number(event.target.value) })}
                  />
                </label>
                <div className="font-style-buttons">
                  <button
                    type="button"
                    className={design.font_weight === "bold" ? "is-active" : ""}
                    onClick={() =>
                      onUpdateDesign({
                        font_weight: design.font_weight === "bold" ? "regular" : "bold",
                        lbl_bold: design.font_weight !== "bold",
                      })
                    }
                    aria-label="볼드"
                  >
                    <Bold size={15} />
                  </button>
                  <button
                    type="button"
                    className={design.lbl_italic ? "is-active" : ""}
                    onClick={() => onUpdateDesign({ lbl_italic: !design.lbl_italic })}
                    aria-label="기울임"
                  >
                    <Italic size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="control-section">
          <div className="section-heading">
            <div>
              <span>02</span>
              <strong>중심점과 원자료</strong>
            </div>
          </div>
          <div className="switch-stack">
            <ToggleSwitch
              label="모음 중심점 표시"
              checked={design.show_centroid}
              onChange={() => onUpdateDesign({ show_centroid: !design.show_centroid })}
            />
            <ToggleSwitch
              label="원자료 점 표시"
              checked={design.show_raw}
              onChange={() => onUpdateDesign({ show_raw: !design.show_raw })}
            />
          </div>
          <label className="control-label">모음 중심점 모양</label>
          <MarkerPicker
            value={design.centroid_marker}
            onChange={(centroid_marker) => onUpdateDesign({ centroid_marker })}
          />
          <label className="control-label">원자료 점 모양</label>
          <div className="segmented-row">
            <button
              type="button"
              className={design.raw_marker === "o" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ raw_marker: "o" })}
            >
              빈 원
            </button>
            <button
              type="button"
              className={design.raw_marker === "x" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ raw_marker: "x" })}
            >
              가위표
            </button>
            <button
              type="button"
              className={design.raw_marker === "a" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ raw_marker: "a" })}
            >
              라벨
            </button>
          </div>
          <div className="palette-picker-row">
            <PalettePicker
              label="원자료 색상"
              value={design.raw_color}
              onChange={(raw_color) => raw_color && onUpdateDesign({ raw_color })}
            />
          </div>
        </section>

        <section className="control-section">
          <div className="section-heading">
            <div>
              <span>03</span>
              <strong>신뢰 타원</strong>
            </div>
          </div>
          <div className="segmented-row">
            <button
              type="button"
              className={design.ell_thick === 0.5 ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_thick: 0.5 })}
            >
              얇게
            </button>
            <button
              type="button"
              className={design.ell_thick === 1 ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_thick: 1 })}
            >
              보통
            </button>
            <button
              type="button"
              className={design.ell_thick === 2 ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_thick: 2 })}
            >
              굵게
            </button>
          </div>
          <div className="segmented-row">
            <button
              type="button"
              className={design.ell_style === "-" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_style: "-" })}
            >
              실선
            </button>
            <button
              type="button"
              className={design.ell_style === "---" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_style: "---" })}
            >
              긴 점선
            </button>
            <button
              type="button"
              className={design.ell_style === "--" || design.ell_style === ":" ? "is-active" : ""}
              onClick={() => onUpdateDesign({ ell_style: "--" })}
            >
              짧은 점선
            </button>
          </div>
          <div className="palette-picker-row">
            <PalettePicker
              label="선 색상"
              value={design.ell_color}
              onChange={(ell_color) => onUpdateDesign({ ell_color })}
              allowTransparent
            />
            <PalettePicker
              label="채우기"
              value={design.ell_fill_color}
              onChange={(ell_fill_color) => onUpdateDesign({ ell_fill_color })}
              allowTransparent
            />
          </div>
          <label className="opacity-control">
            <span>
              채우기 투명도 <b>{Math.round(design.ell_fill_opacity * 100)}%</b>
            </span>
            <input
              type="range"
              min="0"
              max="60"
              value={design.ell_fill_opacity * 100}
              onChange={(event) => onUpdateDesign({ ell_fill_opacity: Number(event.target.value) / 100 })}
            />
          </label>
        </section>

        <section className="control-section">
          <div className="section-heading">
            <div>
              <span>04</span>
              <strong>플롯 배경과 축</strong>
            </div>
          </div>
          <div className="switch-stack">
            <ToggleSwitch
              label="격자 표시"
              checked={design.show_grid}
              onChange={() => onUpdateDesign({ show_grid: !design.show_grid })}
            />
            <ToggleSwitch
              label="테두리 축"
              checked={design.box_spines}
              onChange={() => onUpdateDesign({ box_spines: !design.box_spines })}
            />
            <ToggleSwitch
              label="축 단위 표시"
              checked={design.show_axis_units}
              onChange={() => onUpdateDesign({ show_axis_units: !design.show_axis_units })}
            />
          </div>
          <label className="opacity-control">
            <span>
              눈금 숫자 크기 <b>{Number(design.tick_label_size ?? 13)}pt</b>
            </span>
            <input
              type="range"
              min="10"
              max="18"
              step="1"
              value={Number(design.tick_label_size ?? 13)}
              onChange={(event) => onUpdateDesign({ tick_label_size: Number(event.target.value) })}
            />
          </label>
          {design.show_grid ? (
            <label className="opacity-control">
              <span>
                격자 투명도 <b>{Math.round(design.grid_opacity * 100)}%</b>
              </span>
              <input
                type="range"
                min="5"
                max="80"
                value={design.grid_opacity * 100}
                onChange={(event) => onUpdateDesign({ grid_opacity: Number(event.target.value) / 100 })}
              />
            </label>
          ) : null}
        </section>

        <details className="advanced-options">
          <summary>
            고급 옵션 <ChevronDown size={14} />
          </summary>
          <div className="advanced-body">
            <div className="switch-stack">
              <ToggleSwitch
                label="라벨 슬래시 감싸기"
                checked={design.label_slash_wrap}
                onChange={() => onUpdateDesign({ label_slash_wrap: !design.label_slash_wrap })}
              />
              <ToggleSwitch
                label="보조 눈금"
                checked={design.show_minor_ticks}
                onChange={() => onUpdateDesign({ show_minor_ticks: !design.show_minor_ticks })}
              />
              <ToggleSwitch
                label="축 위치 반전"
                checked={design.axis_position_swap}
                onChange={() => onUpdateDesign({ axis_position_swap: !design.axis_position_swap })}
              />
              <ToggleSwitch
                label="세로축 라벨 회전"
                checked={design.y_label_rotation}
                onChange={() => onUpdateDesign({ y_label_rotation: !design.y_label_rotation })}
              />
            </div>
          </div>
        </details>
      </fieldset>
      <div className="global-design-actions">
        <button type="button" className="wide-action" onClick={onReset}>
          <RefreshCcw size={14} /> 광역 디자인 초기화
        </button>
        <button
          type="button"
          className={`global-design-lock ${globalDesignLocked ? "is-locked" : ""}`}
          onClick={onToggleLock}
          aria-pressed={globalDesignLocked}
          title={globalDesignLocked ? "설정 유지 ON" : "설정 유지 OFF"}
        >
          {globalDesignLocked ? <Lock size={14} /> : <Unlock size={14} />}
          <span>설정 유지</span>
        </button>
      </div>
    </>
  );
}
