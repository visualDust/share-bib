import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Card,
  Upload,
  Button,
  Input,
  Progress,
  Toast,
  Typography,
  Descriptions,
  RadioGroup,
  Radio,
} from "@douyinfe/semi-ui-19";
import { IconUpload } from "@douyinfe/semi-icons";
import client from "../api/client";
import { useInterval } from "../hooks/usePolling";
import DuplicateReviewModal from "../components/DuplicateReviewModal";
import "../styles/glass.css";

const { Title, Text } = Typography;

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

export default function Import() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [collectionName, setCollectionName] = useState("");
  const [duplicateStrategy, setDuplicateStrategy] =
    useState<DuplicateStrategy>("manual");
  const [importing, setImporting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [showDuplicateReview, setShowDuplicateReview] = useState(false);

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
            Toast.success(t("import.importComplete"));
            const colId = res.data.result?.collection_id;
            if (colId) {
              setTimeout(() => navigate(`/collections/${colId}`), 800);
            }
          } else {
            Toast.error(t("import.importFailed"));
          }
        }
      } catch {
        /* ignore */
      }
    },
    taskId ? 2000 : null,
  );

  const handleImport = async () => {
    if (!file) {
      Toast.warning(t("import.selectFile"));
      return;
    }

    // If manual mode, scan first
    if (duplicateStrategy === "manual") {
      setImporting(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
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
        Toast.error(err.response?.data?.detail || t("import.scanFailed"));
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

    if (collectionName) formData.append("collection_name", collectionName);
    formData.append("duplicate_strategy", duplicateStrategy);

    if (Object.keys(decisions).length > 0) {
      formData.append("duplicate_decisions", JSON.stringify(decisions));
    }

    try {
      const res = await client.post("/import/bibtex", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTaskId(res.data.task_id);
      setResult(res.data);
      setScanResult(null);
      setShowDuplicateReview(false);
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("import.importFailed"));
      setImporting(false);
    }
  };

  const progress = result?.result?.progress;

  return (
    <div className="import-container">
      <Title heading={3} style={{ marginBottom: 24 }}>
        {t("import.title")}
      </Title>
      <Card className="glass-card">
        <Upload
          draggable
          accept=".bib"
          limit={1}
          action=""
          uploadTrigger="custom"
          dragMainText={t("import.dragText")}
          dragSubText={t("import.dragSubText")}
          onFileChange={(files) => setFile(files?.[0] || null)}
          disabled={importing}
        />
        <div style={{ marginTop: 16 }}>
          <label
            style={{
              display: "block",
              marginBottom: 4,
              fontSize: 14,
              color: "var(--semi-color-text-0)",
            }}
          >
            {t("import.collectionName")}
          </label>
          <Input
            placeholder={t("import.autoGenerate")}
            value={collectionName}
            onChange={setCollectionName}
            disabled={importing}
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <label
            style={{
              display: "block",
              marginBottom: 8,
              fontSize: 14,
              color: "var(--semi-color-text-0)",
            }}
          >
            {t("import.strategy.label")}
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
              {t("import.strategy.keepExisting")}
            </Radio>
            <Radio value="use_new">{t("import.strategy.useNew")}</Radio>
            <Radio value="manual">{t("import.strategy.manual")}</Radio>
          </RadioGroup>
        </div>
        <Button
          theme="solid"
          icon={<IconUpload />}
          onClick={handleImport}
          loading={importing}
          disabled={!file || importing || result?.status === "completed"}
          style={{ marginTop: 16 }}
          block
        >
          {t("import.startImport")}
        </Button>
      </Card>

      {result && (
        <Card className="import-result glass-card">
          <Title heading={5}>{t("import.resultTitle")}</Title>
          {result.status === "processing" && (
            <div>
              <Text>{t("import.processing")}</Text>
              <Progress percent={-1} style={{ marginTop: 8 }} />
            </div>
          )}
          {result.status === "completed" && progress && (
            <div>
              <Descriptions
                data={[
                  { key: t("import.totalEntries"), value: progress.total },
                  { key: t("import.successImported"), value: progress.success },
                  { key: t("import.skipped"), value: progress.skipped },
                ]}
                row
                size="small"
              />
              {result.result?.errors && result.result.errors.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <Text type="warning">{t("import.skippedEntries")}</Text>
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
              {result.result?.collection_id && (
                <Button
                  theme="solid"
                  style={{ marginTop: 16 }}
                  onClick={() =>
                    navigate(`/collections/${result.result!.collection_id}`)
                  }
                >
                  {t("import.viewCollection")}
                </Button>
              )}
            </div>
          )}
          {result.status === "failed" && (
            <Text type="danger">
              {result.result?.error || t("import.importFailed")}
            </Text>
          )}
        </Card>
      )}

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
    </div>
  );
}
