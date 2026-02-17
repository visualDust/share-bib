import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { Switch } from "@douyinfe/semi-ui-19";
import { ThemeContext, useTheme } from "../hooks/useTheme";
import { flushSync } from "react-dom";

export function SwitchColorMode() {
  const { darkMode, setDarkMode } = useTheme();

  return (
    <Switch
      checked={darkMode}
      onChange={(val, e) =>
        setDarkMode(val, e.nativeEvent as unknown as React.MouseEvent)
      }
      checkedText="🌚"
      uncheckedText="😎"
      aria-label="Toggle theme"
    />
  );
}

export function ThemeContextProvider({ children }: { children: ReactNode }) {
  const [darkModeState, setDarkModeState] = useState(() => {
    const saved = localStorage.getItem("paper-col-theme");
    return saved === "dark" || saved === null;
  });

  useEffect(() => {
    const body = document.body;
    if (darkModeState) {
      body.setAttribute("theme-mode", "dark");
    } else {
      body.removeAttribute("theme-mode");
    }
  }, [darkModeState]);

  const setDarkMode = useCallback(
    (val: boolean, mouseEvent?: React.MouseEvent) => {
      const setTheme = () => {
        setDarkModeState(val);
        localStorage.setItem("paper-col-theme", val ? "dark" : "light");
      };

      // @ts-ignore - View Transitions API
      if (document.startViewTransition) {
        // @ts-ignore
        document.startViewTransition(() => {
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
    [],
  );

  return (
    <ThemeContext.Provider value={{ darkMode: darkModeState, setDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
}
