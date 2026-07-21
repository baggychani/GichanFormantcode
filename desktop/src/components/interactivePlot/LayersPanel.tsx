import type React from "react";
import type {
  CSSProperties,
  Dispatch,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
  SetStateAction,
} from "react";
import {
  Bold,
  ChevronDown,
  Eye,
  EyeOff,
  GripVertical,
  Italic,
  Lock,
  RefreshCcw,
  Unlock,
  X,
} from "lucide-react";
import {
  DESIGN_EFFECT_LABELS,
  DESIGN_EFFECT_ORDER,
  effectDisplayValue,
  FONT_FAMILIES,
  FONT_WEIGHT_LABELS,
  FONT_WEIGHTS,
  fontFamilyStyle,
  normalizedFontWeight,
} from "./designDefaults";
import type { DesignSettings, LayerOverrides, LayerVisibility } from "./types";
import { MarkerPicker, PalettePicker, ToggleSwitch } from "./widgets";

export function LayersPanel({
  layerListHeight,
  selectedLayer,
  selectedLocked,
  effective,
  updateLayerDesign,
  resetSelectedLayer,
  clearLayerSelection,
  beginLayerPanelResize,
  resizeLayerPanels,
  endLayerPanelResize,
  cancelLayerPanelResize,
  toggleAllLayerEyes,
  toggleAllLayerSemi,
  resetLayerOrder,
  layerListRef,
  layerOrder,
  layerState,
  lockedLayers,
  layerOverrides,
  expandedLayers,
  setExpandedLayers,
  selectedLayers,
  draggingLayer,
  dropTarget,
  layerRowRefs,
  draggingLayerRef,
  cancelLayerDrag,
  beginLayerDrag,
  moveLayerDrag,
  commitLayerDrag,
  moveLayerByStep,
  toggleLayerEye,
  toggleLayerSemi,
  selectLayer,
  toggleLock,
  removeLayerEffect,
}: {
  layerListHeight: number;
  selectedLayer: string;
  selectedLocked: boolean;
  effective: (key: keyof DesignSettings) => DesignSettings[keyof DesignSettings];
  updateLayerDesign: (patch: Partial<DesignSettings>) => void;
  resetSelectedLayer: () => void;
  clearLayerSelection: () => void;
  beginLayerPanelResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  resizeLayerPanels: (event: ReactPointerEvent<HTMLDivElement>) => void;
  endLayerPanelResize: (event: ReactPointerEvent<HTMLDivElement>) => void;
  cancelLayerPanelResize: () => void;
  toggleAllLayerEyes: () => void;
  toggleAllLayerSemi: () => void;
  resetLayerOrder: () => void;
  layerListRef: React.RefObject<HTMLDivElement | null>;
  layerOrder: string[];
  layerState: Record<string, LayerVisibility>;
  lockedLayers: Set<string>;
  layerOverrides: LayerOverrides;
  expandedLayers: Set<string>;
  setExpandedLayers: Dispatch<SetStateAction<Set<string>>>;
  selectedLayers: Set<string>;
  draggingLayer: string | null;
  dropTarget: { vowel: string; after: boolean } | null;
  layerRowRefs: React.MutableRefObject<Map<string, HTMLDivElement>>;
  draggingLayerRef: React.MutableRefObject<string | null>;
  cancelLayerDrag: () => void;
  beginLayerDrag: (event: ReactPointerEvent<HTMLButtonElement>, vowel: string) => void;
  moveLayerDrag: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  commitLayerDrag: (event: { pointerId?: number; preventDefault?: () => void }) => void;
  moveLayerByStep: (vowel: string, direction: -1 | 1) => void;
  toggleLayerEye: (vowel: string) => void;
  toggleLayerSemi: (vowel: string) => void;
  selectLayer: (vowel: string, event: ReactMouseEvent<HTMLButtonElement>) => void;
  toggleLock: (vowel: string) => void | Promise<void>;
  removeLayerEffect: (vowel: string, key: keyof DesignSettings) => void;
}) {
  return (
    <div
      className="layer-split-layout"
      style={{ "--layer-list-height": `${layerListHeight}px` } as CSSProperties}
    >
      <div className="layer-inspector-scroll">
        {selectedLayer ? (
          <div className={`selected-layer-design ${selectedLocked ? "is-locked" : ""}`}>
            <div className="selected-layer-heading">
              <div>
                <span>선택 레이어</span>
                <strong>{selectedLayer}</strong>
              </div>
              {selectedLocked ? (
                <span>
                  <Lock size={12} /> 잠김
                </span>
              ) : (
                <button type="button" onClick={resetSelectedLayer}>
                  <RefreshCcw size={13} /> 초기화
                </button>
              )}
            </div>
            <fieldset className="layer-design-form" disabled={selectedLocked}>
              <div className="palette-picker-row">
                <PalettePicker
                  label="라벨 색상"
                  value={String(effective("lbl_color"))}
                  onChange={(lbl_color) => lbl_color && updateLayerDesign({ lbl_color })}
                  disabled={selectedLocked}
                />
              </div>
              <div className="text-style-block">
                <span className="control-label">텍스트 설정</span>
                <div className="font-controls font-family-row">
                  <select
                    value={String(effective("font_family"))}
                    onChange={(event) => {
                      const font_family = event.target.value;
                      updateLayerDesign({
                        font_family,
                        font_style: fontFamilyStyle(font_family),
                        font_weight: normalizedFontWeight(font_family, effective("font_weight")),
                      });
                    }}
                    aria-label="글꼴"
                  >
                    {FONT_FAMILIES.map((family) => (
                      <option key={family}>{family}</option>
                    ))}
                  </select>
                  <select
                    value={normalizedFontWeight(String(effective("font_family")), effective("font_weight"))}
                    onChange={(event) =>
                      updateLayerDesign({
                        font_weight: event.target.value as DesignSettings["font_weight"],
                        lbl_bold: event.target.value === "bold",
                      })
                    }
                    disabled={(FONT_WEIGHTS[String(effective("font_family"))] ?? []).length <= 1}
                    aria-label="Weight"
                  >
                    {(FONT_WEIGHTS[String(effective("font_family"))] ?? ["regular"]).map((weight) => (
                      <option key={weight} value={weight}>
                        {FONT_WEIGHT_LABELS[weight]}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="font-size-row">
                  <label className="font-size-control">
                    <span className="font-control-caption">
                      크기 <b>{Number(effective("lbl_size"))}pt</b>
                    </span>
                    <input
                      type="range"
                      min="12"
                      max="28"
                      step="1"
                      value={Number(effective("lbl_size"))}
                      onChange={(event) => updateLayerDesign({ lbl_size: Number(event.target.value) })}
                    />
                  </label>
                  <div className="font-style-buttons">
                    <button
                      type="button"
                      className={effective("font_weight") === "bold" ? "is-active" : ""}
                      onClick={() =>
                        updateLayerDesign({
                          font_weight: effective("font_weight") === "bold" ? "regular" : "bold",
                          lbl_bold: effective("font_weight") !== "bold",
                        })
                      }
                      aria-label="볼드"
                    >
                      <Bold size={15} />
                    </button>
                    <button
                      type="button"
                      className={effective("lbl_italic") ? "is-active" : ""}
                      onClick={() => updateLayerDesign({ lbl_italic: !effective("lbl_italic") })}
                      aria-label="기울임"
                    >
                      <Italic size={15} />
                    </button>
                  </div>
                </div>
              </div>
              <label className="control-label">중심점 모양</label>
              <MarkerPicker
                value={String(effective("centroid_marker"))}
                onChange={(centroid_marker) => updateLayerDesign({ centroid_marker })}
                disabled={selectedLocked}
              />
              <label className="control-label">신뢰 타원</label>
              <div className="segmented-row">
                <button
                  type="button"
                  className={Number(effective("ell_thick")) === 0.5 ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ ell_thick: 0.5 })}
                >
                  얇게
                </button>
                <button
                  type="button"
                  className={Number(effective("ell_thick")) === 1 ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ ell_thick: 1 })}
                >
                  보통
                </button>
                <button
                  type="button"
                  className={Number(effective("ell_thick")) === 2 ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ ell_thick: 2 })}
                >
                  굵게
                </button>
              </div>
              <div className="segmented-row">
                <button
                  type="button"
                  className={effective("ell_style") === "-" ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ ell_style: "-" })}
                >
                  실선
                </button>
                <button
                  type="button"
                  className={effective("ell_style") === "---" ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ ell_style: "---" })}
                >
                  긴 점선
                </button>
                <button
                  type="button"
                  className={
                    effective("ell_style") === "--" || effective("ell_style") === ":" ? "is-active" : ""
                  }
                  onClick={() => updateLayerDesign({ ell_style: "--" })}
                >
                  짧은 점선
                </button>
              </div>
              <div className="palette-picker-row">
                <PalettePicker
                  label="타원 선"
                  value={effective("ell_color") as string | null}
                  onChange={(ell_color) => updateLayerDesign({ ell_color })}
                  allowTransparent
                  disabled={selectedLocked}
                />
                <PalettePicker
                  label="타원 채우기"
                  value={effective("ell_fill_color") as string | null}
                  onChange={(ell_fill_color) => updateLayerDesign({ ell_fill_color })}
                  allowTransparent
                  disabled={selectedLocked}
                />
              </div>
              <label className="opacity-control">
                <span>
                  레이어 타원 투명도{" "}
                  <b>{Math.round(Number(effective("ell_fill_opacity")) * 100)}%</b>
                </span>
                <input
                  type="range"
                  min="0"
                  max="60"
                  value={Number(effective("ell_fill_opacity")) * 100}
                  onChange={(event) =>
                    updateLayerDesign({ ell_fill_opacity: Number(event.target.value) / 100 })
                  }
                />
              </label>
              <label className="control-label">원자료 점</label>
              <div className="palette-picker-row">
                <PalettePicker
                  label="원자료 색상"
                  value={effective("raw_color") as string}
                  onChange={(raw_color) => raw_color && updateLayerDesign({ raw_color })}
                  disabled={selectedLocked}
                />
              </div>
              <div className="segmented-row">
                <button
                  type="button"
                  className={effective("raw_marker") === "o" ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ raw_marker: "o" })}
                >
                  빈 원
                </button>
                <button
                  type="button"
                  className={effective("raw_marker") === "x" ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ raw_marker: "x" })}
                >
                  가위표
                </button>
                <button
                  type="button"
                  className={effective("raw_marker") === "a" ? "is-active" : ""}
                  onClick={() => updateLayerDesign({ raw_marker: "a" })}
                >
                  라벨
                </button>
              </div>
              <details className="layer-advanced layer-text-options" open>
                <summary>
                  고급 옵션 <ChevronDown size={14} />
                </summary>
                <div className="switch-stack">
                  <ToggleSwitch
                    label="라벨 슬래시 감싸기"
                    checked={Boolean(effective("label_slash_wrap"))}
                    onChange={() =>
                      updateLayerDesign({ label_slash_wrap: !effective("label_slash_wrap") })
                    }
                    disabled={selectedLocked}
                  />
                </div>
              </details>
            </fieldset>
          </div>
        ) : (
          <p className="empty-layers">레이어를 선택하면 디자인을 편집할 수 있습니다.</p>
        )}
      </div>
      <div
        className="layer-splitter"
        role="separator"
        aria-orientation="horizontal"
        aria-label="레이어 디자인과 목록 높이 조절"
        onPointerDown={beginLayerPanelResize}
        onPointerMove={resizeLayerPanels}
        onPointerUp={endLayerPanelResize}
        onPointerCancel={endLayerPanelResize}
        onLostPointerCapture={cancelLayerPanelResize}
      >
        <i />
      </div>
      <div className="layer-list-dock">
        <div className="layer-batch-row">
          <span>일괄 적용</span>
          <button type="button" onClick={toggleAllLayerEyes}>
            <Eye size={14} /> 전체 표시
          </button>
          <button type="button" onClick={toggleAllLayerSemi}>
            반투명
          </button>
        </div>
        <div className="layer-list-toolbar">
          <span>
            <GripVertical size={12} /> 끌어서 순서 변경
          </span>
          <button type="button" onClick={resetLayerOrder}>
            <RefreshCcw size={11} /> 순서 초기화
          </button>
        </div>
        <div
          className="layer-list"
          ref={layerListRef}
          onPointerDown={(event) => {
            if (event.target === event.currentTarget) clearLayerSelection();
          }}
        >
          {layerOrder.length ? (
            layerOrder.map((vowel) => {
              const visibility = layerState[vowel] ?? "ON";
              const locked = lockedLayers.has(vowel);
              const effects = layerOverrides[vowel] ?? {};
              const effectKeys = DESIGN_EFFECT_ORDER.filter((key) => key in effects);
              const expanded = effectKeys.length > 0 && expandedLayers.has(vowel);
              return (
                <div
                  className={`layer-row visibility-${visibility.toLowerCase()} ${selectedLayers.has(vowel) ? "is-selected" : ""} ${draggingLayer === vowel ? "is-dragging" : ""} ${dropTarget?.vowel === vowel ? (dropTarget.after ? "drop-after" : "drop-before") : ""}`}
                  key={vowel}
                  data-layer-vowel={vowel}
                  ref={(element) => {
                    if (element) layerRowRefs.current.set(vowel, element);
                    else layerRowRefs.current.delete(vowel);
                  }}
                >
                  <div
                    className="layer-row-main"
                    onLostPointerCapture={() => {
                      if (draggingLayerRef.current === vowel) cancelLayerDrag();
                    }}
                  >
                    <button
                      type="button"
                      className="layer-drag-handle"
                      onPointerDown={(event) => beginLayerDrag(event, vowel)}
                      onPointerMove={moveLayerDrag}
                      onPointerUp={commitLayerDrag}
                      onPointerCancel={cancelLayerDrag}
                      onKeyDown={(event) => {
                        if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                          event.preventDefault();
                          moveLayerByStep(vowel, event.key === "ArrowUp" ? -1 : 1);
                        }
                      }}
                      aria-label={`${vowel} 레이어 순서 이동`}
                      title="끌어서 이동 · 방향키로 한 칸 이동"
                    >
                      <GripVertical size={15} />
                    </button>
                    <button
                      type="button"
                      className="layer-visibility"
                      onClick={() => toggleLayerEye(vowel)}
                      title={visibility === "OFF" ? "레이어 표시" : "레이어 숨기기"}
                    >
                      {visibility === "OFF" ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                    <button
                      type="button"
                      className={`layer-semi ${visibility === "SEMI" ? "is-active" : ""}`}
                      onClick={() => toggleLayerSemi(vowel)}
                    >
                      반투명
                    </button>
                    <button
                      type="button"
                      className="layer-name"
                      onMouseDown={(event) => {
                        if (event.button === 0) event.preventDefault();
                      }}
                      onClick={(event) => selectLayer(vowel, event)}
                    >
                      <strong>{vowel}</strong>
                    </button>
                    {effectKeys.length ? (
                      <button
                        type="button"
                        className={`layer-expand ${expanded ? "is-expanded" : ""}`}
                        onClick={() =>
                          setExpandedLayers((previous) => {
                            const next = new Set(previous);
                            if (next.has(vowel)) next.delete(vowel);
                            else next.add(vowel);
                            return next;
                          })
                        }
                        aria-label={`${vowel} 디자인 변경 내역 ${expanded ? "접기" : "펼치기"}`}
                      >
                        <ChevronDown size={14} />
                        <span>{effectKeys.length}</span>
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="layer-lock"
                      onClick={() => void toggleLock(vowel)}
                      aria-label={locked ? `${vowel} 레이어 잠금 해제` : `${vowel} 레이어 잠금`}
                    >
                      {locked ? <Lock size={14} /> : <Unlock size={14} />}
                    </button>
                  </div>
                  {expanded ? (
                    <div className="layer-effects" aria-label={`${vowel} 레이어 디자인 변경 내역`}>
                      {effectKeys.map((key) => {
                        const value = effects[key] as DesignSettings[keyof DesignSettings];
                        const isColor =
                          key === "lbl_color" ||
                          key === "ell_color" ||
                          key === "ell_fill_color" ||
                          key === "raw_color";
                        return (
                          <div className="layer-effect-row" key={key}>
                            <span>{DESIGN_EFFECT_LABELS[key] ?? key}</span>
                            <strong>
                              {isColor ? (
                                <>
                                  <i
                                    className={`effect-color ${value === null ? "is-transparent" : ""}`}
                                    style={typeof value === "string" ? { background: value } : undefined}
                                  />
                                  <em>{value === null ? "투명" : String(value).toUpperCase()}</em>
                                </>
                              ) : (
                                effectDisplayValue(key, value)
                              )}
                            </strong>
                            <button
                              type="button"
                              disabled={locked}
                              onClick={() => removeLayerEffect(vowel, key)}
                              aria-label={`${DESIGN_EFFECT_LABELS[key] ?? key} 설정 제거`}
                            >
                              <X size={13} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <p className="empty-layers">현재 파일에서 모음 라벨을 찾지 못했습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}
