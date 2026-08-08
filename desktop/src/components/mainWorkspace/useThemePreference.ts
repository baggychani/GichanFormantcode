import { useCallback, useEffect, useState } from "react";
import { emit } from "@tauri-apps/api/event";

export type Theme = "dark" | "light";

function initialTheme(): Theme {
  const saved = window.localStorage.getItem("gichanformant-theme");
  const theme = saved === "dark" || saved === "light"
    ? saved
    : window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  return theme;
}

export function useThemePreference() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystemTheme = (event: MediaQueryListEvent) => {
      if (window.localStorage.getItem("gichanformant-theme")) return;
      setTheme(event.matches ? "dark" : "light");
    };
    media.addEventListener?.("change", syncSystemTheme);
    return () => media.removeEventListener?.("change", syncSystemTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    // Only an explicit toggle persists a preference. OS changes continue to
    // apply until the user chooses a theme in the app.
    void emit("gichan-theme", theme);
  }, [theme]);

  const toggleThemePreference = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      window.localStorage.setItem("gichanformant-theme", next);
      return next;
    });
  }, []);

  return { theme, toggleThemePreference };
}
