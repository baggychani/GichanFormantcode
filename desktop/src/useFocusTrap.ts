import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Trap Tab focus inside `containerRef` while `active`.
 * Restores prior focus on deactivate. Sets `inert` on siblings of the portal root when possible.
 */
export function useFocusTrap(
  active: boolean,
  containerRef: React.RefObject<HTMLElement | null>,
  options?: { initialFocus?: "first" | "container" },
) {
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const initialFocus = options?.initialFocus ?? "first";

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;

    const focusables = () =>
      Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (node) => !node.hasAttribute("disabled") && node.getAttribute("aria-hidden") !== "true",
      );

    const focusInitial = () => {
      if (initialFocus === "container") {
        if (!container.hasAttribute("tabindex")) container.tabIndex = -1;
        container.focus({ preventScroll: true });
        return;
      }
      const nodes = focusables();
      (nodes[0] ?? container).focus({ preventScroll: true });
    };

    // Defer so dialog content is mounted.
    const frame = window.requestAnimationFrame(focusInitial);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const nodes = focusables();
      if (!nodes.length) {
        event.preventDefault();
        container.focus({ preventScroll: true });
        return;
      }
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      const current = document.activeElement as HTMLElement | null;
      if (event.shiftKey) {
        if (current === first || !container.contains(current)) {
          event.preventDefault();
          last.focus();
        }
      } else if (current === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown, true);

    // Mark background inert when the trap root is a direct overlay sibling.
    const backdrop = container.closest("[data-modal-root]") ?? container.parentElement;
    const inertTargets: HTMLElement[] = [];
    if (backdrop?.parentElement) {
      for (const sibling of Array.from(backdrop.parentElement.children)) {
        if (sibling === backdrop || !(sibling instanceof HTMLElement)) continue;
        if (sibling.hasAttribute("data-modal-root")) continue;
        sibling.setAttribute("inert", "");
        sibling.setAttribute("aria-hidden", "true");
        inertTargets.push(sibling);
      }
    }

    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKeyDown, true);
      for (const node of inertTargets) {
        node.removeAttribute("inert");
        node.removeAttribute("aria-hidden");
      }
      const previous = previousFocusRef.current;
      if (previous && document.contains(previous)) {
        previous.focus({ preventScroll: true });
      }
    };
  }, [active, containerRef, initialFocus]);
}
