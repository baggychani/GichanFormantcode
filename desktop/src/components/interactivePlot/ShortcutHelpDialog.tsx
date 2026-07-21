import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "../../useFocusTrap";

export function ShortcutHelpDialog({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLElement | null>(null);
  useFocusTrap(true, dialogRef);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      onClose();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [onClose]);

  return (
    <div className="shortcut-help-backdrop" data-modal-root role="presentation" onClick={onClose}>
      <section
        ref={dialogRef}
        className="shortcut-help-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcut-help-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span className="section-eyebrow">KEYBOARD</span>
            <h2 id="shortcut-help-title">단축키</h2>
            <p>입력란에 포커스가 있을 때는 일부 키가 무시됩니다.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="닫기">
            <X size={18} />
          </button>
        </header>
        <div className="shortcut-help-body">
          <div className="shortcut-help-group">
            <strong>패널</strong>
            <ul>
              <li>
                <kbd>`</kbd>
                <span>좌·우 패널 접기/펼치기</span>
              </li>
              <li>
                <kbd>A</kbd>
                <span>분석 도구 패널</span>
              </li>
              <li>
                <kbd>D</kbd>
                <span>광역 디자인 패널</span>
              </li>
              <li>
                <kbd>?</kbd>
                <span>이 도움말</span>
              </li>
            </ul>
          </div>
          <div className="shortcut-help-group">
            <strong>도구</strong>
            <ul>
              <li>
                <kbd>R</kbd>
                <span>눈금자</span>
              </li>
              <li>
                <kbd>T</kbd>
                <span>라벨 이동</span>
              </li>
              <li>
                <kbd>P</kbd>
                <span>그리기 모드</span>
              </li>
              <li>
                <kbd>1</kbd>–<kbd>5</kbd>
                <span>그리기 도구 (선·영역·텍스트·기준선·범례)</span>
              </li>
              <li>
                <kbd>Esc</kbd>
                <span>도구 취소 · 레이어 선택 해제</span>
              </li>
            </ul>
          </div>
          <div className="shortcut-help-group">
            <strong>레이어</strong>
            <ul>
              <li>
                <kbd>Ctrl</kbd>+<kbd>C</kbd>
                <span>선택 레이어 설정 복사</span>
              </li>
              <li>
                <kbd>Ctrl</kbd>+<kbd>V</kbd>
                <span>레이어 설정 붙여넣기 (기존 설정 덮어씀)</span>
              </li>
            </ul>
          </div>
          <div className="shortcut-help-group">
            <strong>파일</strong>
            <ul>
              <li>
                <kbd>←</kbd> <kbd>→</kbd>
                <span>이전/다음 파일</span>
              </li>
              <li>
                <kbd>Home</kbd> / <kbd>End</kbd>
                <span>첫/마지막 파일</span>
              </li>
              <li>
                <kbd>Ctrl</kbd>+<kbd>S</kbd>
                <span>프로젝트 저장</span>
              </li>
              <li>
                <kbd>M</kbd>
                <span>다중 플롯 (파일 2개 이상)</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
