import {
  Modal,
  Table,
  Radio,
  Button,
  Tag,
  Typography,
  Space,
} from "@douyinfe/semi-ui-19";
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

interface DuplicateInfo {
  entry_id: string;
  new_title: string;
  existing_paper_id: string;
  existing_title: string;
  match_type: "bibtex_key" | "arxiv_id" | "doi" | "title";
  match_value: string;
  new_authors?: string[];
  existing_authors?: string[];
  new_year?: number;
  existing_year?: number;
  new_venue?: string;
  existing_venue?: string;
}

interface Props {
  visible: boolean;
  duplicates: DuplicateInfo[];
  onConfirm: (
    decisions: Record<string, "keep_existing" | "use_new" | "skip">,
  ) => void;
  onCancel: () => void;
}

export default function DuplicateReviewModal({
  visible,
  duplicates,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  const [decisions, setDecisions] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    duplicates.forEach((d) => {
      initial[d.entry_id] = "keep_existing";
    });
    return initial;
  });

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (visible) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [visible]);

  const matchTypeColors: Record<string, any> = {
    bibtex_key: "blue",
    arxiv_id: "green",
    doi: "purple",
    title: "orange",
  };

  const applyToAll = (decision: string) => {
    const all: Record<string, string> = {};
    duplicates.forEach((d) => {
      all[d.entry_id] = decision;
    });
    setDecisions(all);
  };

  const columns = [
    {
      title: t("duplicateReview.matchType.label"),
      dataIndex: "match_type",
      width: 110,
      render: (type: string) => (
        <Tag color={matchTypeColors[type]}>
          {t(`duplicateReview.matchType.${type}`)}
        </Tag>
      ),
    },
    {
      title: t("duplicateReview.existing"),
      width: 280,
      render: (record: DuplicateInfo) => (
        <div>
          <Typography.Text strong>{record.existing_title}</Typography.Text>
          <div
            style={{
              fontSize: 12,
              color: "var(--semi-color-text-2)",
              marginTop: 4,
            }}
          >
            {record.existing_authors?.join(", ")} · {record.existing_year} ·{" "}
            {record.existing_venue}
          </div>
        </div>
      ),
    },
    {
      title: t("duplicateReview.new"),
      width: 280,
      render: (record: DuplicateInfo) => (
        <div>
          <Typography.Text strong>{record.new_title}</Typography.Text>
          <div
            style={{
              fontSize: 12,
              color: "var(--semi-color-text-2)",
              marginTop: 4,
            }}
          >
            {record.new_authors?.join(", ")} · {record.new_year} ·{" "}
            {record.new_venue}
          </div>
        </div>
      ),
    },
    {
      title: t("duplicateReview.action.label"),
      width: 320,
      render: (record: DuplicateInfo) => (
        <Radio.Group
          value={decisions[record.entry_id]}
          onChange={(e) =>
            setDecisions((prev) => ({
              ...prev,
              [record.entry_id]: e.target.value,
            }))
          }
          style={{ display: "flex", flexWrap: "nowrap", gap: "8px" }}
        >
          <Radio value="keep_existing">
            {t("duplicateReview.action.keepExisting")}
          </Radio>
          <Radio value="use_new">{t("duplicateReview.action.useNew")}</Radio>
          <Radio value="skip">{t("duplicateReview.action.skip")}</Radio>
        </Radio.Group>
      ),
    },
  ];

  return (
    <Modal
      title={t("duplicateReview.title")}
      visible={visible}
      onCancel={onCancel}
      onOk={() => onConfirm(decisions as any)}
      okText={t("duplicateReview.confirm")}
      cancelText={t("duplicateReview.cancel")}
      className="dedup-modal"
      width={window.innerWidth < 768 ? "100vw" : 900}
      fullScreen={window.innerWidth < 768}
      style={{ maxHeight: window.innerWidth < 768 ? undefined : "85vh" }}
      maskClosable={false}
    >
      <div style={{ padding: "0 20px" }}>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
          {t("duplicateReview.subtitle", { count: duplicates.length })}
        </Typography.Paragraph>
        <Space style={{ marginBottom: 16 }}>
          <Typography.Text strong>
            {t("duplicateReview.quickActions")}:
          </Typography.Text>
          <Button
            size="small"
            theme="solid"
            type="primary"
            onClick={() => applyToAll("keep_existing")}
          >
            {t("duplicateReview.action.keepExisting")}
          </Button>
          <Button
            size="small"
            theme="solid"
            type="secondary"
            onClick={() => applyToAll("use_new")}
          >
            {t("duplicateReview.action.useNew")}
          </Button>
          <Button
            size="small"
            theme="solid"
            type="tertiary"
            onClick={() => applyToAll("skip")}
          >
            {t("duplicateReview.action.skip")}
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={duplicates}
        pagination={false}
        rowKey="entry_id"
        size="small"
      />
    </Modal>
  );
}
