import { createContext, useContext } from "react";

export type ThemePreference = "auto" | "light" | "dark";

export const ThemeContext = createContext<{
  darkMode: boolean;
  themePreference: ThemePreference;
  setThemePreference: (preference: ThemePreference) => void;
  setDarkMode: (val: boolean, mouseEvent?: React.MouseEvent) => void;
}>(null!);

export function useTheme() {
  return useContext(ThemeContext);
}
