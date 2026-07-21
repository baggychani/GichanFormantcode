import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { SourceInfo } from "../../../../ipc/protocol";

export function FileSelectMenu({
  sources,
  currentIndex,
  onNavigate,
  disabled = false,
}: {
  sources: SourceInfo[];
  currentIndex: number;
  onNavigate: (index: number) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const current = sources[currentIndex];

  useEffect(() => {
    if (!open) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => window.removeEventListener("pointerdown", closeOnOutsidePointer);
  }, [open]);

  return (
    <div className={`file-select-menu ${open ? "is-open" : ""}`} ref={rootRef}>
      <button
        type="button"
        className="file-select-trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
      >
        <span>{current?.name ?? "데이터 파일을 불러오세요"}</span>
        <ChevronDown size={14} />
      </button>
      {open ? (
        <div className="file-option-menu" role="listbox" aria-label="파일 선택">
          {sources.map((source) => (
            <button
              type="button"
              role="option"
              aria-selected={source.index === currentIndex}
              className={source.index === currentIndex ? "is-selected" : ""}
              key={`${source.index}-${source.name}`}
              onClick={() => {
                setOpen(false);
                onNavigate(source.index);
              }}
            >
              {source.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
