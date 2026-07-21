import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowLeftRight, CircleHelp, X } from "lucide-react";
import { barkToHz, hzToBark } from "../../plotUnits";

type AnchorRect = { top: number; left: number };

/** Hz ↔ Bark converter card opened from `?` beside the range heading. */
export function UnitConverterPopover() {
  const [open, setOpen] = useState(false);
  const [hz, setHz] = useState("");
  const [bark, setBark] = useState("");
  const [lastFocus, setLastFocus] = useState<"hz" | "bark">("hz");
  const [anchor, setAnchor] = useState<AnchorRect | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const launchRef = useRef<HTMLButtonElement | null>(null);
  const hzRef = useRef<HTMLInputElement | null>(null);

  const clearFields = () => {
    setHz("");
    setBark("");
    setLastFocus("hz");
  };

  const close = () => {
    clearFields();
    setOpen(false);
  };

  const syncAnchor = () => {
    const rect = launchRef.current?.getBoundingClientRect();
    if (!rect) return;
    const rail = launchRef.current?.closest(".plot-control-rail") as HTMLElement | null;
    const railRight = rail?.getBoundingClientRect().right ?? rect.right;
    setAnchor({
      top: Math.max(12, rect.top - 8),
      left: Math.min(window.innerWidth - 248, railRight + 10),
    });
  };

  useLayoutEffect(() => {
    if (!open) return;
    syncAnchor();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      close();
    };
    const onReposition = () => syncAnchor();
    window.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("resize", onReposition);
    window.addEventListener("scroll", onReposition, true);
    const focusTimer = window.setTimeout(() => hzRef.current?.focus(), 0);
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("resize", onReposition);
      window.removeEventListener("scroll", onReposition, true);
    };
  }, [open]);

  const convert = () => {
    try {
      const hzText = hz.trim();
      const barkText = bark.trim();
      if (lastFocus === "bark" && barkText) {
        setHz(barkToHz(Number(barkText)).toFixed(1));
        return;
      }
      if (hzText) {
        setBark(hzToBark(Number(hzText)).toFixed(2));
        return;
      }
      if (barkText) setHz(barkToHz(Number(barkText)).toFixed(1));
    } catch {
      /* ignore non-numeric input, same as PySide */
    }
  };

  return (
    <div className="unit-converter-plugin" ref={rootRef}>
      <button
        ref={launchRef}
        type="button"
        className={`unit-converter-launch ${open ? "is-active" : ""}`}
        aria-label="Hz · Bark 변환기"
        aria-expanded={open}
        aria-controls="unit-converter-popover"
        title="Hz · Bark 변환기"
        onClick={() => {
          if (open) close();
          else setOpen(true);
        }}
      >
        <CircleHelp size={13} strokeWidth={2.2} />
      </button>
      {open && anchor ? (
        <aside
          id="unit-converter-popover"
          className="unit-converter-popover"
          role="dialog"
          aria-label="Hz Bark 변환기"
          style={{ top: anchor.top, left: anchor.left }}
        >
          <header>
            <strong>단위 변환</strong>
            <button type="button" onClick={close} aria-label="닫기">
              <X size={14} />
            </button>
          </header>
          <p>Hz ↔ Bark 값을 쉽게 변환해 보세요.</p>
          <div className="unit-converter-row">
            <label>
              <span>Hz</span>
              <input
                ref={hzRef}
                value={hz}
                inputMode="decimal"
                placeholder="—"
                onFocus={() => setLastFocus("hz")}
                onChange={(event) => setHz(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    convert();
                  }
                }}
              />
            </label>
            <button
              type="button"
              className="unit-converter-swap"
              onClick={convert}
              aria-label="단위 변환"
              title="변환"
            >
              <ArrowLeftRight size={15} />
            </button>
            <label>
              <span>Bark</span>
              <input
                value={bark}
                inputMode="decimal"
                placeholder="—"
                onFocus={() => setLastFocus("bark")}
                onChange={(event) => setBark(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    convert();
                  }
                }}
              />
            </label>
          </div>
          <small>마지막에 편집한 칸 기준으로 반대 단위를 채웁니다.</small>
        </aside>
      ) : null}
    </div>
  );
}
