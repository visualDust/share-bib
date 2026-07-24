import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import zh from "./zh.json";
import en from "./en.json";

export type LanguagePreference = "auto" | "zh" | "en";

const detectBrowserLanguage = () =>
  navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";

export const getLanguagePreference = (): LanguagePreference => {
  const saved = localStorage.getItem("sharebib-language-preference");
  return saved === "zh" || saved === "en" ? saved : "auto";
};

export const resolveLanguagePreference = (preference: LanguagePreference) =>
  preference === "auto" ? detectBrowserLanguage() : preference;

i18n.use(initReactI18next).init({
  resources: { zh: { translation: zh }, en: { translation: en } },
  fallbackLng: "zh",
  lng: resolveLanguagePreference(getLanguagePreference()),
  interpolation: { escapeValue: false },
});

window.addEventListener("languagechange", () => {
  if (getLanguagePreference() === "auto") {
    void i18n.changeLanguage(detectBrowserLanguage());
  }
});

export default i18n;
