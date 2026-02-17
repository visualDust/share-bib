import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  SideSheet,
  Button,
  Typography,
  Toast,
  TagInput,
  TextArea,
  Input,
  Select,
} from "@douyinfe/semi-ui-19";
import client from "../api/client";
import "../styles/glass.css";
import "../index.css";

const { Title } = Typography;

const isMobile = () => window.innerWidth < 768;

interface PaperData {
  id: string;
  title: string;
  authors: string[] | null;
  venue: string | null;
  year: number | null;
  summary: string | null;
  tags: string[] | null;
  urls: Record<string, string | null>;
  status: string;
}

interface Props {
  visible: boolean;
  paper: PaperData | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function PaperEditSheet({
  visible,
  paper,
  onClose,
  onSaved,
}: Props) {
  const { t } = useTranslation();
  const [mobile, setMobile] = useState(isMobile());
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [urlArxiv, setUrlArxiv] = useState("");
  const [urlPdf, setUrlPdf] = useState("");
  const [urlCode, setUrlCode] = useState("");
  const [urlProject, setUrlProject] = useState("");
  const [status, setStatus] = useState("no_access");

  useEffect(() => {
    if (paper) {
      setTitle(paper.title || "");
      setSummary(paper.summary || "");
      setTags(paper.tags || []);
      setUrlArxiv(paper.urls?.arxiv || "");
      setUrlPdf(paper.urls?.pdf || "");
      setUrlCode(paper.urls?.code || "");
      setUrlProject(paper.urls?.project || "");
      setStatus(paper.status || "no_access");
    }

    const handleResize = () => setMobile(isMobile());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [paper]);

  const handleSave = async () => {
    if (!paper) return;
    setSaving(true);
    try {
      await client.put(`/papers/${paper.id}`, {
        title,
        summary: summary || null,
        tags,
        url_arxiv: urlArxiv || null,
        url_pdf: urlPdf || null,
        url_code: urlCode || null,
        url_project: urlProject || null,
        status,
      });
      Toast.success(t("paperEdit.saveSuccess"));
      onSaved();
      onClose();
    } catch {
      Toast.error(t("paperEdit.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const footer = (
    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
      <Button onClick={onClose}>{t("paperEdit.cancel")}</Button>
      <Button theme="solid" onClick={handleSave} loading={saving}>
        {t("paperEdit.save")}
      </Button>
    </div>
  );

  return (
    <SideSheet
      title={<Title heading={5}>{t("paperEdit.title")}</Title>}
      visible={visible}
      onCancel={onClose}
      footer={footer}
      size={mobile ? "large" : "medium"}
      width={mobile ? "100vw" : undefined}
      headerStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
      bodyStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label className="form-label">{t("paperEdit.labelTitle")}</label>
          <Input value={title} onChange={setTitle} />
        </div>
        <div>
          <label className="form-label">{t("paperEdit.labelSummary")}</label>
          <TextArea value={summary} onChange={setSummary} rows={4} />
        </div>
        <div>
          <label className="form-label">{t("paperEdit.labelTags")}</label>
          <TagInput
            value={tags}
            onChange={(v) => setTags(v as string[])}
            placeholder={t("paperEdit.tagPlaceholder")}
          />
        </div>
        <div>
          <label className="form-label">{t("paperEdit.labelStatus")}</label>
          <Select
            value={status}
            onChange={(v) => setStatus(v as string)}
            style={{ width: "100%" }}
          >
            <Select.Option value="accessible">
              {t("paperEdit.accessible")}
            </Select.Option>
            <Select.Option value="no_access">
              {t("paperEdit.noAccess")}
            </Select.Option>
          </Select>
        </div>
        <div>
          <label className="form-label">arXiv URL</label>
          <Input
            value={urlArxiv}
            onChange={setUrlArxiv}
            placeholder="https://arxiv.org/abs/..."
          />
        </div>
        <div>
          <label className="form-label">PDF URL</label>
          <Input
            value={urlPdf}
            onChange={setUrlPdf}
            placeholder="https://arxiv.org/pdf/..."
          />
        </div>
        <div>
          <label className="form-label">Code URL</label>
          <Input
            value={urlCode}
            onChange={setUrlCode}
            placeholder="https://github.com/..."
          />
        </div>
        <div>
          <label className="form-label">Project URL</label>
          <Input
            value={urlProject}
            onChange={setUrlProject}
            placeholder="https://..."
          />
        </div>
      </div>
    </SideSheet>
  );
}
