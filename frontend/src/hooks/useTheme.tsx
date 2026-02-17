import { createContext, useContext } from "react";

export const ThemeContext = createContext<{
  darkMode: boolean;
  setDarkMode: (val: boolean, mouseEvent?: React.MouseEvent) => void;
}>(null!);

export function useTheme() {
  return useContext(ThemeContext);
}
