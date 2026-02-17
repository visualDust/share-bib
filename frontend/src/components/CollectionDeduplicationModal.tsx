import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Modal,
  Table,
  Button,
  Typography,
  Space,
  Toast,
  Spin,
  Tag,
  Card,
} from "@douyinfe/semi-ui-19";
import client from "../api/client";

const { Text } = Typography;

const isMobile = () => window.innerWidth < 768;

interface DuplicateGroup {
  paper1_id: string;
  paper1_title: string;
  paper1_authors: string[] | null;
  paper1_year: number | null;
  paper1_venue: string | null;
  paper2_id: string;
  paper2_title: string;
  paper2_authors: string[] | null;
  paper2_year: number | null;
  paper2_venue: string | null;
  match_type: "bibtex_key" | "arxiv_id" | "doi" | "title";
  match_value: string;
}

interface Props {
  visible: boolean;
  collectionId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CollectionDeduplicationModal({
  visible,
  collectionId,
  onClose,
  onSuccess,
}: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [keptPairs, setKeptPairs] = useState<Set<string>>(new Set()); // Track pairs marked as "keep both"
  const [removing, setRemoving] = useState(false);
  const [mobile, setMobile] = useState(isMobile());

  useEffect(() => {
    if (visible) {
      document.body.style.overflow = "hidden";
      loadDuplicates();
    } else {
      document.body.style.overflow = "";
    }

    const handleResize = () => setMobile(isMobile());
    window.addEventListener("resize", handleResize);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("resize", handleResize);
    };
  }, [visible, collectionId]);

  const loadDuplicates = async () => {
    setLoading(true);
    try {
      const res = await client.get(`/collections/${collectionId}/duplicates`);
      setDuplicates(res.data.duplicates);
      setSelectedPapers(new Set());
      setKeptPairs(new Set());
    } catch (error: any) {
      Toast.error(
        error.response?.data?.detail || t("collectionDedup.loadError"),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async () => {
    if (selectedPapers.size === 0) {
      Toast.warning(t("collectionDedup.selectPapers"));
      return;
    }

    setRemoving(true);
    try {
      await client.post(
        `/collections/${collectionId}/remove-duplicates`,
        Array.from(selectedPapers),
      );
      Toast.success(
        t("collectionDedup.removeSuccess", { count: selectedPapers.size }),
      );
      onSuccess();
      onClose();
    } catch (error: any) {
      Toast.error(
        error.response?.data?.detail || t("collectionDedup.removeError"),
      );
    } finally {
      setRemoving(false);
    }
  };

  const togglePaper = (paperId: string, pairKey: string) => {
    const newSelected = new Set(selectedPapers);
    const newKept = new Set(keptPairs);

    // Remove from kept pairs if this pair was marked as "keep both"
    newKept.delete(pairKey);

    if (newSelected.has(paperId)) {
      newSelected.delete(paperId);
    } else {
      newSelected.add(paperId);
    }
    setSelectedPapers(newSelected);
    setKeptPairs(newKept);
  };

  const keepBoth = (pairKey: string, paper1Id: string, paper2Id: string) => {
    const newSelected = new Set(selectedPapers);
    const newKept = new Set(keptPairs);

    // Remove both papers from selection
    newSelected.delete(paper1Id);
    newSelected.delete(paper2Id);

    // Mark this pair as kept
    newKept.add(pairKey);

    setSelectedPapers(newSelected);
    setKeptPairs(newKept);
  };

  const getMatchTypeLabel = (matchType: string) => {
    const labels: Record<string, string> = {
      bibtex_key: t("collectionDedup.matchType.bibtexKey"),
      arxiv_id: t("collectionDedup.matchType.arxivId"),
      doi: t("collectionDedup.matchType.doi"),
      title: t("collectionDedup.matchType.title"),
    };
    return labels[matchType] || matchType;
  };

  const getMatchTypeColor = (
    matchType: string,
  ): "blue" | "green" | "orange" | "purple" | "grey" => {
    const colors: Record<
      string,
      "blue" | "green" | "orange" | "purple" | "grey"
    > = {
      bibtex_key: "blue",
      arxiv_id: "green",
      doi: "orange",
      title: "purple",
    };
    return colors[matchType] || "grey";
  };

  const renderMobileCard = (record: DuplicateGroup) => {
    const pairKey = `${record.paper1_id}-${record.paper2_id}`;
    const isKept = keptPairs.has(pairKey);
    const paper1Selected = selectedPapers.has(record.paper1_id);
    const paper2Selected = selectedPapers.has(record.paper2_id);

    return (
      <Card
        key={pairKey}
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: 16 }}
      >
        <div style={{ marginBottom: 12 }}>
          <Tag color={getMatchTypeColor(record.match_type)}>
            {getMatchTypeLabel(record.match_type)}
          </Tag>
        </div>

        <div
          style={{
            marginBottom: 16,
            paddingBottom: 16,
            borderBottom: "1px solid var(--semi-color-border)",
          }}
        >
          <Text strong style={{ display: "block", marginBottom: 4 }}>
            {t("collectionDedup.paper1")}
          </Text>
          <Text style={{ display: "block", marginBottom: 4 }}>
            {record.paper1_title}
          </Text>
          <Text
            size="small"
            type="secondary"
            style={{ display: "block", marginBottom: 2 }}
          >
            {record.paper1_authors?.join(", ") || "Unknown"}
          </Text>
          <Text size="small" type="tertiary">
            {record.paper1_venue || "Unknown"} ·{" "}
            {record.paper1_year || "Unknown"}
          </Text>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ display: "block", marginBottom: 4 }}>
            {t("collectionDedup.paper2")}
          </Text>
          <Text style={{ display: "block", marginBottom: 4 }}>
            {record.paper2_title}
          </Text>
          <Text
            size="small"
            type="secondary"
            style={{ display: "block", marginBottom: 2 }}
          >
            {record.paper2_authors?.join(", ") || "Unknown"}
          </Text>
          <Text size="small" type="tertiary">
            {record.paper2_venue || "Unknown"} ·{" "}
            {record.paper2_year || "Unknown"}
          </Text>
        </div>

        <Space vertical style={{ width: "100%" }}>
          <Space style={{ width: "100%" }}>
            <Button
              size="small"
              type={paper1Selected ? "danger" : "tertiary"}
              onClick={() => togglePaper(record.paper1_id, pairKey)}
              disabled={isKept}
              style={{ flex: 1 }}
            >
              {paper1Selected
                ? t("collectionDedup.selected")
                : t("collectionDedup.remove")}{" "}
              1
            </Button>
            <Button
              size="small"
              type={paper2Selected ? "danger" : "tertiary"}
              onClick={() => togglePaper(record.paper2_id, pairKey)}
              disabled={isKept}
              style={{ flex: 1 }}
            >
              {paper2Selected
                ? t("collectionDedup.selected")
                : t("collectionDedup.remove")}{" "}
              2
            </Button>
          </Space>
          <Button
            size="small"
            type={isKept ? "primary" : "tertiary"}
            onClick={() =>
              keepBoth(pairKey, record.paper1_id, record.paper2_id)
            }
            block
          >
            {isKept
              ? t("collectionDedup.keeping")
              : t("collectionDedup.keepBoth")}
          </Button>
        </Space>
      </Card>
    );
  };

  const columns = [
    {
      title: t("collectionDedup.matchReason"),
      dataIndex: "match_type",
      render: (matchType: string) => (
        <Tag color={getMatchTypeColor(matchType)}>
          {getMatchTypeLabel(matchType)}
        </Tag>
      ),
    },
    {
      title: t("collectionDedup.paper1"),
      dataIndex: "paper1",
      render: (_: any, record: DuplicateGroup) => (
        <div>
          <Text strong>{record.paper1_title}</Text>
          <br />
          <Text size="small" type="secondary">
            {record.paper1_authors?.join(", ") || "Unknown"}
          </Text>
          <br />
          <Text size="small" type="tertiary">
            {record.paper1_venue || "Unknown"} ·{" "}
            {record.paper1_year || "Unknown"}
          </Text>
        </div>
      ),
    },
    {
      title: t("collectionDedup.paper2"),
      dataIndex: "paper2",
      render: (_: any, record: DuplicateGroup) => (
        <div>
          <Text strong>{record.paper2_title}</Text>
          <br />
          <Text size="small" type="secondary">
            {record.paper2_authors?.join(", ") || "Unknown"}
          </Text>
          <br />
          <Text size="small" type="tertiary">
            {record.paper2_venue || "Unknown"} ·{" "}
            {record.paper2_year || "Unknown"}
          </Text>
        </div>
      ),
    },
    {
      title: t("collectionDedup.action"),
      dataIndex: "action",
      render: (_: any, record: DuplicateGroup) => {
        const pairKey = `${record.paper1_id}-${record.paper2_id}`;
        const isKept = keptPairs.has(pairKey);
        const paper1Selected = selectedPapers.has(record.paper1_id);
        const paper2Selected = selectedPapers.has(record.paper2_id);

        return (
          <Space vertical align="start" style={{ width: "100%" }}>
            <Space style={{ width: "100%" }}>
              <Button
                size="small"
                type={paper1Selected ? "danger" : "tertiary"}
                onClick={() => togglePaper(record.paper1_id, pairKey)}
                disabled={isKept}
              >
                {paper1Selected
                  ? t("collectionDedup.selected")
                  : t("collectionDedup.remove")}{" "}
                1
              </Button>
              <Button
                size="small"
                type={paper2Selected ? "danger" : "tertiary"}
                onClick={() => togglePaper(record.paper2_id, pairKey)}
                disabled={isKept}
              >
                {paper2Selected
                  ? t("collectionDedup.selected")
                  : t("collectionDedup.remove")}{" "}
                2
              </Button>
            </Space>
            <Button
              size="small"
              type={isKept ? "primary" : "tertiary"}
              onClick={() =>
                keepBoth(pairKey, record.paper1_id, record.paper2_id)
              }
              block
            >
              {isKept
                ? t("collectionDedup.keeping")
                : t("collectionDedup.keepBoth")}
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <Modal
      title={t("collectionDedup.title")}
      visible={visible}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>{t("collectionDedup.cancel")}</Button>
          <Button
            type="danger"
            onClick={handleRemove}
            loading={removing}
            disabled={selectedPapers.size === 0}
          >
            {t("collectionDedup.removeSelected", {
              count: selectedPapers.size,
            })}
          </Button>
        </Space>
      }
      width="90vw"
      style={{ maxWidth: "1200px", maxHeight: "90vh" }}
      bodyStyle={{ padding: "16px", overflow: "hidden" }}
      maskClosable={false}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          <Spin size="large" />
        </div>
      ) : duplicates.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          <Text type="secondary">{t("collectionDedup.noDuplicates")}</Text>
        </div>
      ) : (
        <>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            {t("collectionDedup.subtitle", { count: duplicates.length })}
          </Typography.Paragraph>
          <div style={{ maxHeight: "calc(90vh - 280px)", overflow: "auto" }}>
            {mobile ? (
              duplicates.map(renderMobileCard)
            ) : (
              <Table
                columns={columns}
                dataSource={duplicates}
                pagination={false}
                rowKey={(record) =>
                  record ? `${record.paper1_id}-${record.paper2_id}` : ""
                }
                size="small"
              />
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
