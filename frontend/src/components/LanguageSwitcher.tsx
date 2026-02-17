import { useTranslation } from "react-i18next";
import { Button } from "@douyinfe/semi-ui-19";
import { IconLanguage } from "@douyinfe/semi-icons";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const toggle = () =>
    i18n.changeLanguage(i18n.language === "zh" ? "en" : "zh");

  return (
    <Button
      icon={<IconLanguage />}
      theme="borderless"
      onClick={toggle}
      style={{ fontSize: 12 }}
    >
      {i18n.language === "zh" ? "EN" : "中"}
    </Button>
  );
}
