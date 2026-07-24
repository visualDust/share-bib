import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { Switch } from "@douyinfe/semi-ui-19";
import { IconMoon, IconSun } from "@douyinfe/semi-icons";
import {
  ThemeContext,
  type ThemePreference,
  useTheme,
} from "../hooks/useTheme";
import { flushSync } from "react-dom";

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => void) => unknown;
};

export function SwitchColorMode() {
  const { darkMode, setDarkMode } = useTheme();

  return (
    <Switch
      checked={darkMode}
      onChange={(val, e) =>
        setDarkMode(val, e.nativeEvent as unknown as React.MouseEvent)
      }
      checkedText={<IconMoon size="small" />}
      uncheckedText={<IconSun size="small" />}
      aria-label="Toggle theme"
    />
  );
}

export function ThemeContextProvider({ children }: { children: ReactNode }) {
  const [themePreference, setThemePreferenceState] = useState<ThemePreference>(
    () => {
      const saved = localStorage.getItem("paper-col-theme");
      return saved === "dark" || saved === "light" || saved === "auto"
        ? saved
        : "auto";
    },
  );
  const [systemDarkMode, setSystemDarkMode] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const darkModeState =
    themePreference === "dark" ||
    (themePreference === "auto" && systemDarkMode);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) =>
      setSystemDarkMode(event.matches);
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const body = document.body;
    if (darkModeState) {
      body.setAttribute("theme-mode", "dark");
    } else {
      body.removeAttribute("theme-mode");
    }
  }, [darkModeState]);

  const setThemePreference = useCallback((preference: ThemePreference) => {
    setThemePreferenceState(preference);
    localStorage.setItem("paper-col-theme", preference);
  }, []);

  const setDarkMode = useCallback(
    (val: boolean, mouseEvent?: React.MouseEvent) => {
      const setTheme = () => {
        setThemePreference(val ? "dark" : "light");
      };

      const startViewTransition = (document as ViewTransitionDocument)
        .startViewTransition;
      if (startViewTransition) {
        startViewTransition.call(document, () => {
          flushSync(() => {
            setTheme();
            if (mouseEvent?.clientX !== undefined) {
              document.documentElement.style.setProperty(
                "--page-theme-changing-origin",
                `${mouseEvent.clientX}px ${mouseEvent.clientY}px`,
              );
            } else {
              document.documentElement.style.setProperty(
                "--page-theme-changing-origin",
                "50% 50%",
              );
            }
          });
        });
      } else {
        setTheme();
      }
    },
    [setThemePreference],
  );

  return (
    <ThemeContext.Provider
      value={{
        darkMode: darkModeState,
        themePreference,
        setThemePreference,
        setDarkMode,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
