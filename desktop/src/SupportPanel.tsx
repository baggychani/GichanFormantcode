import { useEffect, useRef, useState } from "react";
import { Check, Copy, X } from "lucide-react";
import { SUPPORT } from "./support";
import { useFocusTrap } from "./useFocusTrap";
import "./SupportPanel.css";

type SupportPanelProps = {
  open: boolean;
  onClose: () => void;
  onCopied?: () => void;
};

async function copyAccountNumber(): Promise<boolean> {
  const text = SUPPORT.accountCopy;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch {
      return false;
    }
  }
}

export function SupportPanel({ open, onClose, onCopied }: SupportPanelProps) {
  const panelRef = useRef<HTMLElement | null>(null);
  const [copied, setCopied] = useState(false);
  useFocusTrap(open, panelRef);

  useEffect(() => {
    if (!open) {
      setCopied(false);
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="support-backdrop" role="presentation" onClick={onClose}>
      <section
        ref={panelRef}
        className="support-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="support-panel-header">
          <div>
            <h2 id="support-title">후원</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="닫기">
            <X size={15} />
          </button>
        </header>

        <p className="support-copy">
          GichanFormant는 무료입니다. 도움이 되셨다면 커피 한 잔 정도로 응원해 주세요!
        </p>

        <div className="support-account" aria-label="후원 계좌">
          <span className="support-bank">{SUPPORT.bank}</span>
          <strong className="support-number">{SUPPORT.accountDisplay}</strong>
          <span className="support-holder">{SUPPORT.holder}</span>
        </div>

        <button
          type="button"
          className={`support-copy-btn primary-button ${copied ? "is-copied" : ""}`}
          onClick={() => {
            void copyAccountNumber().then((ok) => {
              if (!ok) return;
              setCopied(true);
              onCopied?.();
              window.setTimeout(() => setCopied(false), 1800);
            });
          }}
        >
          {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
          {copied ? "복사됨" : "계좌번호 복사"}
        </button>
      </section>
    </div>
  );
}
