import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Input,
  Select,
  InputNumber,
  TagInput,
  Collapsible,
} from "@douyinfe/semi-ui-19";
import { IconHelpCircle } from "@douyinfe/semi-icons";

interface ConfigField {
  key: string;
  label: string;
  field_type: string;
  required: boolean;
  default: unknown;
  description: string;
  options: { value: string; label: string }[] | null;
  min_value: number | null;
  max_value: number | null;
}

interface SourceConfigFormProps {
  fields: ConfigField[];
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export default function SourceConfigForm({
  fields,
  value,
  onChange,
}: SourceConfigFormProps) {
  const handleChange = (key: string, val: unknown) => {
    onChange({ ...value, [key]: val });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {fields.map((f) => (
        <div key={f.key}>
          <div style={{ marginBottom: 4, fontWeight: 500 }}>
            {f.label}
            {f.required && (
              <span style={{ color: "var(--semi-color-danger)" }}> *</span>
            )}
          </div>
          {f.description && (
            <div
              style={{
                fontSize: 12,
                color: "var(--semi-color-text-2)",
                marginBottom: 4,
              }}
            >
              {f.description}
            </div>
          )}
          {renderField(f, value[f.key], (val) => handleChange(f.key, val))}
        </div>
      ))}
    </div>
  );
}

function renderField(
  field: ConfigField,
  value: unknown,
  onChange: (val: unknown) => void,
) {
  switch (field.field_type) {
    case "multiselect":
      return (
        <Select
          multiple
          filter
          style={{ width: "100%" }}
          optionList={(field.options || []).map((o) => ({
            value: o.value,
            label: o.label,
          }))}
          value={(value as string[]) || []}
          onChange={(val) => onChange(val)}
          maxTagCount={5}
        />
      );
    case "keywords":
      return <KeywordsField value={value} onChange={onChange} />;
    case "number":
      return (
        <InputNumber
          style={{ width: "100%" }}
          value={(value as number) ?? field.default ?? undefined}
          onChange={(val) => onChange(val)}
          min={field.min_value ?? undefined}
          max={field.max_value ?? undefined}
        />
      );
    case "text":
    default:
      return (
        <Input
          style={{ width: "100%" }}
          value={(value as string) || ""}
          onChange={(val) => onChange(val)}
        />
      );
  }
}

function KeywordsField({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (val: unknown) => void;
}) {
  const { t } = useTranslation();
  const [showHelp, setShowHelp] = useState(false);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <TagInput
          style={{ flex: 1 }}
          value={(value as string[]) || []}
          onChange={(val) => onChange(val)}
          placeholder={t("crawl.keywordsPlaceholder")}
        />
        <IconHelpCircle
          style={{
            cursor: "pointer",
            color: "var(--semi-color-text-2)",
            flexShrink: 0,
          }}
          onClick={() => setShowHelp(!showHelp)}
        />
      </div>
      <Collapsible isOpen={showHelp}>
        <div
          style={{
            marginTop: 8,
            padding: "8px 12px",
            borderRadius: 6,
            background: "var(--semi-color-fill-0)",
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 2 }}>
            {t("crawl.keywordsHelpTitle")}
          </div>
          <div>
            <code>keyword</code> — {t("crawl.keywordsHelpOr")}
          </div>
          <div>
            <code>+keyword</code> — {t("crawl.keywordsHelpAnd")}
          </div>
          <div>
            <code>-keyword</code> — {t("crawl.keywordsHelpNot")}
          </div>
          <div>
            <code>*</code> — {t("crawl.keywordsHelpWild")}
          </div>
          <div style={{ marginTop: 4, color: "var(--semi-color-text-2)" }}>
            {t("crawl.keywordsHelpExample")}
          </div>
        </div>
      </Collapsible>
    </div>
  );
}
