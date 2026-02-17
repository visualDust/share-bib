import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  SideSheet,
  Button,
  Upload,
  RadioGroup,
  Radio,
  Progress,
  Toast,
  Typography,
  Descriptions,
  Input,
  Checkbox,
} from "@douyinfe/semi-ui-19";
import { IconPlus, IconLink } from "@douyinfe/semi-icons";
import client from "../api/client";
import { useInterval } from "../hooks/usePolling";
import DuplicateReviewModal from "./DuplicateReviewModal";
import "../styles/glass.css";
import "../index.css";

const { Title, Text } = Typography;

const isMobile = () => window.innerWidth < 768;

type PaperSource = "bibtex" | "arxiv";
type DuplicateStrategy = "keep_existing" | "use_new" | "manual";

interface ImportResult {
  task_id: string;
  status: string;
  result?: {
    collection_id?: string;
    progress?: {
      total: number;
      processed: number;
      success: number;
      skipped: number;
    };
    errors?: { entry_id: string; reason: string }[];
    duplicates?: any[];
    error?: string;
  };
}

interface ScanResult {
  scan_id: string;
  total: number;
  duplicates: any[];
  new_papers: number;
}

interface Props {
  visible: boolean;
  collectionId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddPapersSheet({
  visible,
  collectionId,
  onClose,
  onSuccess,
}: Props) {
  const [source, setSource] = useState<PaperSource>("bibtex");
  const [file, setFile] = useState<File | null>(null);
  const [duplicateStrategy, setDuplicateStrategy] =
    useState<DuplicateStrategy>("manual");
  const [skipCollectionDuplicates, setSkipCollectionDuplicates] =
    useState(true);
  const [importing, setImporting] = useState(false);
  const [mobile, setMobile] = useState(isMobile());
  const [taskId, setTaskId] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [showDuplicateReview, setShowDuplicateReview] = useState(false);
  const [arxivUrl, setArxivUrl] = useState("");
  const [arxivLoading, setArxivLoading] = useState(false);
  const [arxivResult, setArxivResult] = useState<{
    ok: boolean;
    title?: string;
    skipped?: boolean;
    message?: string;
    error?: string;
  } | null>(null);

  const { t } = useTranslation();

  useEffect(() => {
    const handleResize = () => setMobile(isMobile());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useInterval(
    async () => {
      if (!taskId) return;
      try {
        const res = await client.get(`/import/tasks/${taskId}`);
        setResult(res.data);
        if (res.data.status === "completed" || res.data.status === "failed") {
          setTaskId(null);
          setImporting(false);
          if (res.data.status === "completed") {
            Toast.success(t("addPapers.importComplete"));
            onSuccess();
          } else {
            Toast.error(t("addPapers.importFailed"));
          }
        }
      } catch {
        /* ignore */
      }
    },
    taskId ? 2000 : null,
  );

  const handleBibtexImport = async () => {
    if (!file) {
      Toast.warning(t("addPapers.selectFile"));
      return;
    }

    // If manual mode, scan first
    if (duplicateStrategy === "manual") {
      setImporting(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("collection_id", collectionId);
        const res = await client.post("/import/bibtex/scan", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setScanResult(res.data);
        setImporting(false);

        if (res.data.duplicates.length > 0) {
          setShowDuplicateReview(true);
          return;
        }
        // No duplicates, proceed directly
      } catch (err: any) {
        Toast.error(err.response?.data?.detail || t("addPapers.scanFailed"));
        setImporting(false);
        return;
      }
    }

    // Execute import (auto mode or manual with no duplicates)
    executeImport({});
  };

  const executeImport = async (decisions: Record<string, string>) => {
    setImporting(true);
    setResult(null);
    const formData = new FormData();

    if (scanResult) {
      formData.append("scan_id", scanResult.scan_id);
    } else {
      formData.append("file", file!);
    }

    formData.append("duplicate_strategy", duplicateStrategy);
    formData.append(
      "skip_collection_duplicates",
      String(skipCollectionDuplicates),
    );

    if (Object.keys(decisions).length > 0) {
      formData.append("duplicate_decisions", JSON.stringify(decisions));
    }

    try {
      const res = await client.post(
        `/import/bibtex/${collectionId}`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
      setTaskId(res.data.task_id);
      setResult(res.data);
      setScanResult(null);
      setShowDuplicateReview(false);
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("addPapers.importFailed"));
      setImporting(false);
    }
  };

  const handleArxivImport = async () => {
    if (!arxivUrl.trim()) {
      Toast.warning(t("addPapers.enterArxivUrl"));
      return;
    }
    setArxivLoading(true);
    setArxivResult(null);
    try {
      const res = await client.post(`/import/arxiv/${collectionId}`, {
        url: arxivUrl.trim(),
      });
      setArxivResult(res.data);
      if (res.data.skipped) {
        setArxivResult({
          ...res.data,
          error: res.data.message || t("addPapers.paperInCollection"),
        });
      } else {
        Toast.success(t("addPapers.paperAdded", { title: res.data.title }));
        setArxivUrl("");
        onSuccess();
      }
    } catch (err: any) {
      setArxivResult({
        ok: false,
        error: err.response?.data?.detail || t("addPapers.importFailed"),
      });
    } finally {
      setArxivLoading(false);
    }
  };

  const handleClose = () => {
    if (!importing && !arxivLoading) {
      setFile(null);
      setDuplicateStrategy("keep_existing");
      setSkipCollectionDuplicates(true);
      setResult(null);
      setTaskId(null);
      setScanResult(null);
      setShowDuplicateReview(false);
      setArxivUrl("");
      setArxivResult(null);
      onClose();
    }
  };

  const progress = result?.result?.progress;

  return (
    <SideSheet
      title={<Title heading={5}>{t("addPapers.title")}</Title>}
      visible={visible}
      onCancel={handleClose}
      size={mobile ? "large" : "medium"}
      width={mobile ? "100vw" : undefined}
      headerStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
      bodyStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
      footer={null}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label className="form-label">{t("addPapers.source")}</label>
          <RadioGroup
            type="button"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            disabled={importing}
          >
            <Radio value="bibtex">{t("addPapers.bibtexFile")}</Radio>
            <Radio value="arxiv">{t("addPapers.arxivLink")}</Radio>
          </RadioGroup>
        </div>

        {source === "bibtex" && (
          <>
            <Upload
              draggable
              accept=".bib"
              limit={1}
              action=""
              uploadTrigger="custom"
              dragMainText={t("addPapers.dragText")}
              dragSubText={t("addPapers.dragSubText")}
              onFileChange={(files) => setFile(files?.[0] || null)}
              disabled={importing}
            />
            <div>
              <label className="form-label">
                {t("addPapers.strategy.label")}
              </label>
              <RadioGroup
                type="button"
                value={duplicateStrategy}
                onChange={(e) =>
                  setDuplicateStrategy(e.target.value as DuplicateStrategy)
                }
                disabled={importing}
              >
                <Radio value="keep_existing">
                  {t("addPapers.strategy.keepExisting")}
                </Radio>
                <Radio value="use_new">{t("addPapers.strategy.useNew")}</Radio>
                <Radio value="manual">{t("addPapers.strategy.manual")}</Radio>
              </RadioGroup>
            </div>
            <Checkbox
              checked={skipCollectionDuplicates}
              onChange={(e) =>
                setSkipCollectionDuplicates(e.target?.checked ?? false)
              }
              disabled={importing}
            >
              {t("addPapers.skipInCollection")}
            </Checkbox>
            <Button
              theme="solid"
              icon={<IconPlus />}
              onClick={handleBibtexImport}
              loading={importing}
              disabled={!file || importing}
              block
            >
              {t("addPapers.startImport")}
            </Button>
          </>
        )}

        {source === "arxiv" && (
          <>
            <div>
              <label className="form-label">{t("addPapers.arxivLabel")}</label>
              <Input
                placeholder="https://arxiv.org/abs/2301.12345"
                value={arxivUrl}
                onChange={setArxivUrl}
                disabled={arxivLoading}
                onEnterPress={handleArxivImport}
              />
            </div>
            <Button
              theme="solid"
              icon={<IconLink />}
              onClick={handleArxivImport}
              loading={arxivLoading}
              disabled={!arxivUrl.trim() || arxivLoading}
              block
            >
              {t("addPapers.addPaper")}
            </Button>
            {arxivResult && (
              <div
                style={{
                  marginTop: 8,
                  padding: 12,
                  borderRadius: 8,
                  backgroundColor: arxivResult.error
                    ? "var(--semi-color-danger-light-default)"
                    : "var(--semi-color-success-light-default)",
                }}
              >
                {arxivResult.error ? (
                  <Text type="danger">{arxivResult.error}</Text>
                ) : arxivResult.skipped ? (
                  <Text type="warning">{arxivResult.message}</Text>
                ) : (
                  <Text type="success">
                    {t("addPapers.paperAdded", { title: arxivResult.title })}
                  </Text>
                )}
              </div>
            )}
          </>
        )}

        {result && (
          <div style={{ marginTop: 8 }}>
            {result.status === "processing" && (
              <div>
                <Text>{t("addPapers.processing")}</Text>
                <Progress percent={-1} style={{ marginTop: 8 }} />
              </div>
            )}
            {result.status === "completed" && progress && (
              <div>
                <Descriptions
                  data={[
                    { key: t("addPapers.totalEntries"), value: progress.total },
                    {
                      key: t("addPapers.successImported"),
                      value: progress.success,
                    },
                    { key: t("addPapers.skipped"), value: progress.skipped },
                  ]}
                  row
                  size="small"
                />
                {result.result?.errors && result.result.errors.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Text type="warning">{t("addPapers.skippedEntries")}</Text>
                    {result.result.errors.map((e, i) => (
                      <div
                        key={i}
                        style={{
                          fontSize: 12,
                          color: "var(--semi-color-text-2)",
                        }}
                      >
                        {e.entry_id}: {e.reason}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {result.status === "failed" && (
              <Text type="danger">
                {result.result?.error || t("addPapers.importFailed")}
              </Text>
            )}
          </div>
        )}
      </div>

      <DuplicateReviewModal
        visible={showDuplicateReview}
        duplicates={scanResult?.duplicates || []}
        onConfirm={(decisions) => executeImport(decisions)}
        onCancel={() => {
          setShowDuplicateReview(false);
          setScanResult(null);
          setImporting(false);
        }}
      />
    </SideSheet>
  );
}
