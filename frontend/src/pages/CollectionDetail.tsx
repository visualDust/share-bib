import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Tag,
  Button,
  Input,
  Dropdown,
  Empty,
  Spin,
  Toast,
  Modal,
} from "@douyinfe/semi-ui-19";
import {
  IconSearch,
  IconLink,
  IconCode,
  IconArrowLeft,
  IconEdit,
  IconDelete,
  IconSetting,
  IconPlus,
  IconFilter,
  IconDownload,
  IconSort,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import PaperEditSheet from "../components/PaperEditSheet";
import CollectionEditSheet from "../components/CollectionEditSheet";
import AddPapersSheet from "../components/AddPapersSheet";
import "../styles/glass.css";

const { Text, Paragraph, Title } = Typography;

const isMobile = () => window.innerWidth < 768;

interface PaperItem {
  id: string;
  title: string;
  authors: string[] | null;
  venue: string | null;
  year: number | null;
  status: string;
  urls: Record<string, string | null>;
  summary: string | null;
  tags: string[] | null;
  added_at: string | null;
  group_tag: string | null;
}
interface Section {
  name: string | null;
  papers: PaperItem[];
}
interface Group {
  name: string | null;
  tag: string | null;
  sections: Section[];
}
interface CollectionData {
  id: string;
  title: string;
  description: string | null;
  created_by: {
    user_id: string;
    username: string;
    display_name: string | null;
  };
  visibility: string;
  allow_export: boolean;
  task_type: string;
  task_source_display: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
  stats: { total: number; accessible: number; no_access: number };
  groups: Group[];
  permissions: any[];
  current_user_permission: string | null;
}

export default function CollectionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CollectionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<
    "title" | "year" | "authors" | "venue" | "added"
  >("added");
  const [editingPaper, setEditingPaper] = useState<PaperItem | null>(null);
  const [showCollectionEdit, setShowCollectionEdit] = useState(false);
  const [showAddPapers, setShowAddPapers] = useState(false);
  const [deletingPaper, setDeletingPaper] = useState<PaperItem | null>(null);
  const [mobile, setMobile] = useState(isMobile());
  const { t } = useTranslation();

  const isLoggedIn = !!localStorage.getItem("token");
  const canEdit = data?.current_user_permission === "edit";
  const isCreator =
    data &&
    isLoggedIn &&
    data.created_by.user_id === localStorage.getItem("user_id");
  const canExport = data && (isCreator || data.allow_export);

  const fetchData = useCallback(() => {
    if (!id) return;
    client
      .get(`/collections/${id}`)
      .then((res) => setData(res.data))
      .catch(() => Toast.error(t("collection.loadFailed")))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    fetchData();

    const handleResize = () => setMobile(isMobile());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [fetchData]);

  const handleRemovePaper = async (paperId: string) => {
    try {
      await client.delete(`/collections/${id}/papers/${paperId}`);
      Toast.success(t("collection.removed"));
      setDeletingPaper(null);
      fetchData();
    } catch {
      Toast.error(t("collection.removeFailed"));
    }
  };

  const handleExportBibtex = async () => {
    try {
      const response = await client.get(`/collections/${id}/export/bibtex`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/x-bibtex" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${id}.bib`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      Toast.success(t("collection.exportSuccess"));
    } catch {
      Toast.error(t("collection.exportFailed"));
    }
  };

  if (loading)
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );
  if (!data) return <Empty description={t("collection.notFound")} />;

  const filterPaper = (p: PaperItem) => {
    if (search) {
      const q = search.toLowerCase();
      if (
        !p.title.toLowerCase().includes(q) &&
        !(p.authors || []).some((a) => a.toLowerCase().includes(q)) &&
        !(p.summary || "").toLowerCase().includes(q)
      )
        return false;
    }
    if (tagFilter) {
      const paperTags = getAllTags(p);
      if (!paperTags.includes(tagFilter)) return false;
    }
    return true;
  };

  const sourceTagLabel = (tag: string | null) => {
    switch (tag) {
      case "imported":
        return t("collection.sourceImported");
      case "arxiv":
        return "arXiv";
      default:
        return tag || t("collection.sourceManual");
    }
  };

  // Get all tags for a paper (user tags + source tag + status tag)
  const getAllTags = (p: PaperItem): string[] => {
    const tags: string[] = [...(p.tags || [])];
    tags.push(sourceTagLabel(p.group_tag));
    tags.push(
      p.status === "accessible"
        ? t("collection.statusAccessible")
        : t("collection.statusNoAccess"),
    );
    return tags;
  };

  // Flatten groups → single paper list, carrying group_tag as attribute
  const allPapers: PaperItem[] = data.groups.flatMap((group) =>
    group.sections.flatMap((section) =>
      section.papers.map((p) => ({ ...p, group_tag: group.tag })),
    ),
  );
  const filteredPapers = allPapers.filter(filterPaper);

  // Sort papers
  const sortedPapers = [...filteredPapers].sort((a, b) => {
    switch (sortBy) {
      case "title":
        return a.title.localeCompare(b.title);
      case "year":
        return (b.year || 0) - (a.year || 0);
      case "authors":
        return ((a.authors || [])[0] || "").localeCompare(
          (b.authors || [])[0] || "",
        );
      case "venue":
        return (a.venue || "").localeCompare(b.venue || "");
      case "added":
      default:
        return (b.added_at || "").localeCompare(a.added_at || "");
    }
  });

  // Collect tags by category for the dropdown
  const sourceTags = new Map<string, number>();
  const statusTags = new Map<string, number>();
  const userTags = new Map<string, number>();
  for (const p of allPapers) {
    const src = sourceTagLabel(p.group_tag);
    sourceTags.set(src, (sourceTags.get(src) || 0) + 1);
    const st =
      p.status === "accessible"
        ? t("collection.statusAccessible")
        : t("collection.statusNoAccess");
    statusTags.set(st, (statusTags.get(st) || 0) + 1);
    for (const tag of p.tags || []) {
      userTags.set(tag, (userTags.get(tag) || 0) + 1);
    }
  }

  return (
    <div>
      <div
        className="collection-detail-actions"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Button
          icon={<IconArrowLeft />}
          theme="borderless"
          onClick={() => (isLoggedIn ? navigate("/") : navigate("/login"))}
          style={mobile ? { minWidth: "auto", padding: "8px 12px" } : undefined}
        >
          {mobile
            ? null
            : isLoggedIn
              ? t("collection.back")
              : t("collection.login")}
        </Button>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canExport && (
            <Button
              icon={<IconDownload />}
              theme="solid"
              type="tertiary"
              onClick={handleExportBibtex}
              style={
                mobile ? { minWidth: "auto", padding: "8px 12px" } : undefined
              }
            >
              {mobile ? null : t("collection.exportBibtex")}
            </Button>
          )}
          {canEdit && (
            <>
              <Button
                icon={<IconPlus />}
                theme="solid"
                onClick={() => setShowAddPapers(true)}
                style={
                  mobile ? { minWidth: "auto", padding: "8px 12px" } : undefined
                }
              >
                {mobile ? null : t("collection.addPapers")}
              </Button>
              <Button
                icon={<IconSetting />}
                theme="solid"
                type="secondary"
                onClick={() => setShowCollectionEdit(true)}
                style={
                  mobile ? { minWidth: "auto", padding: "8px 12px" } : undefined
                }
              >
                {mobile ? null : t("collection.editCollection")}
              </Button>
            </>
          )}
        </div>
      </div>
      {!isLoggedIn && (
        <div
          style={{
            padding: "12px 16px",
            marginBottom: 16,
            background: "var(--semi-color-info-light-default)",
            borderRadius: 8,
            color: "var(--semi-color-info)",
            fontSize: 14,
          }}
        >
          {t("collection.loginHint")}
        </div>
      )}
      <div className="collection-detail-header">
        <Title heading={3}>{data.title}</Title>
        {data.description && (
          <Paragraph type="tertiary">{data.description}</Paragraph>
        )}
        <div className="collection-stats">
          <div className="stat-pill stat-pill-accent">
            <span className="stat-pill-number">{data.stats.total}</span>
            <span className="stat-pill-label">
              {t("collection.totalPapers")}
            </span>
          </div>
          <div className="stat-pill">
            <span className="stat-pill-number">{data.stats.accessible}</span>
            <span className="stat-pill-label">
              {t("collection.accessible")}
            </span>
          </div>
          {data.stats.no_access > 0 && (
            <div className="stat-pill stat-pill-warn">
              <span className="stat-pill-number">{data.stats.no_access}</span>
              <span className="stat-pill-label">
                {t("collection.noAccess")}
              </span>
            </div>
          )}
        </div>
        <div className="collection-meta-row">
          {data.tags &&
            data.tags.map((tagItem) => (
              <Tag key={tagItem} size="small" color="blue">
                {tagItem}
              </Tag>
            ))}
          <Tag size="small">
            {data.created_by.display_name || data.created_by.username}
          </Tag>
        </div>
      </div>
      <div className="filter-bar">
        <Input
          prefix={<IconSearch />}
          placeholder={t("collection.searchPapers")}
          value={search}
          onChange={setSearch}
          style={{ width: 280, maxWidth: "100%" }}
        />
        <Dropdown
          trigger="click"
          showTick
          clickToHide
          position="bottomLeft"
          render={
            <Dropdown.Menu style={{ maxHeight: "400px", overflowY: "auto" }}>
              <Dropdown.Title>{t("collection.filterSource")}</Dropdown.Title>
              {[...sourceTags.entries()].map(([tag, count]) => (
                <Dropdown.Item
                  key={`src-${tag}`}
                  active={tagFilter === tag}
                  onClick={() => setTagFilter(tagFilter === tag ? null : tag)}
                >
                  {tag} ({count})
                </Dropdown.Item>
              ))}
              <Dropdown.Divider />
              <Dropdown.Title>{t("collection.filterStatus")}</Dropdown.Title>
              {[...statusTags.entries()].map(([tag, count]) => (
                <Dropdown.Item
                  key={`st-${tag}`}
                  active={tagFilter === tag}
                  onClick={() => setTagFilter(tagFilter === tag ? null : tag)}
                >
                  {tag} ({count})
                </Dropdown.Item>
              ))}
              {userTags.size > 0 && (
                <>
                  <Dropdown.Divider />
                  <Dropdown.Title>{t("collection.filterTags")}</Dropdown.Title>
                  {[...userTags.entries()].map(([tag, count]) => (
                    <Dropdown.Item
                      key={`tag-${tag}`}
                      active={tagFilter === tag}
                      onClick={() =>
                        setTagFilter(tagFilter === tag ? null : tag)
                      }
                    >
                      {tag} ({count})
                    </Dropdown.Item>
                  ))}
                </>
              )}
            </Dropdown.Menu>
          }
        >
          <span style={{ display: "inline-flex" }}>
            <Button
              icon={<IconFilter />}
              theme={tagFilter ? "light" : "borderless"}
            >
              {t("collection.filter")}
            </Button>
          </span>
        </Dropdown>
        <Dropdown
          trigger="click"
          showTick
          clickToHide
          position="bottomLeft"
          render={
            <Dropdown.Menu>
              <Dropdown.Item
                active={sortBy === "added"}
                onClick={() => setSortBy("added")}
              >
                {t("collection.sortAdded")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "title"}
                onClick={() => setSortBy("title")}
              >
                {t("collection.sortTitle")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "year"}
                onClick={() => setSortBy("year")}
              >
                {t("collection.sortYear")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "authors"}
                onClick={() => setSortBy("authors")}
              >
                {t("collection.sortAuthors")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "venue"}
                onClick={() => setSortBy("venue")}
              >
                {t("collection.sortVenue")}
              </Dropdown.Item>
            </Dropdown.Menu>
          }
        >
          <span style={{ display: "inline-flex" }}>
            <Button icon={<IconSort />} theme="borderless">
              {t("collection.sort")}
            </Button>
          </span>
        </Dropdown>
        {tagFilter && (
          <Tag
            size="small"
            color="blue"
            closable
            onClose={() => setTagFilter(null)}
          >
            {tagFilter}
          </Tag>
        )}
      </div>

      {sortedPapers.length === 0 ? (
        <Empty description={t("collection.noPapers")} />
      ) : (
        <div className="glass-table-wrapper">
          <div className="glass-table-header">
            <span>
              {t("collection.paperList", { count: sortedPapers.length })}
            </span>
          </div>
          <div className="glass-table-body">
            {sortedPapers.map((paper) => (
              <div key={paper.id} className="paper-item">
                <div className="paper-title-row">
                  <div style={{ flex: 1 }}>
                    {paper.urls.arxiv || paper.urls.pdf ? (
                      <a
                        href={paper.urls.arxiv || paper.urls.pdf || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontWeight: 500,
                          fontSize: 15,
                          color: "var(--semi-color-link)",
                        }}
                      >
                        {paper.title}
                      </a>
                    ) : (
                      <Text strong style={{ fontSize: 15 }}>
                        {paper.title}
                      </Text>
                    )}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginTop: 4,
                        flexWrap: "wrap",
                      }}
                    >
                      {paper.venue && (
                        <Tag
                          color="cyan"
                          size="small"
                          style={{
                            fontWeight: 500,
                            maxWidth: mobile ? "200px" : "300px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            display: "inline-block",
                          }}
                        >
                          <span title={paper.venue}>{paper.venue}</span>
                        </Tag>
                      )}
                      {paper.year && (
                        <Tag color="purple" size="small">
                          {paper.year}
                        </Tag>
                      )}
                    </div>
                    <div className="paper-meta">
                      {(paper.authors || []).join(", ")}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 4,
                      alignItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Tag size="small" color="blue">
                      {sourceTagLabel(paper.group_tag)}
                    </Tag>
                    <Tag
                      color={paper.status === "accessible" ? "green" : "grey"}
                      size="small"
                    >
                      {paper.status === "accessible"
                        ? t("collection.statusAccessible")
                        : t("collection.statusNoAccess")}
                    </Tag>
                  </div>
                </div>
                {paper.summary && (
                  <Paragraph
                    ellipsis={{ rows: 2, expandable: true }}
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                      color: "var(--semi-color-text-2)",
                    }}
                  >
                    {paper.summary}
                  </Paragraph>
                )}
                <div className="paper-links">
                  {paper.urls.arxiv && (
                    <Button
                      size="small"
                      theme="borderless"
                      icon={<IconLink />}
                      onClick={() => window.open(paper.urls.arxiv!, "_blank")}
                    >
                      arXiv
                    </Button>
                  )}
                  {paper.urls.pdf && (
                    <Button
                      size="small"
                      theme="borderless"
                      onClick={() => window.open(paper.urls.pdf!, "_blank")}
                    >
                      PDF
                    </Button>
                  )}
                  {paper.urls.code && (
                    <Button
                      size="small"
                      theme="borderless"
                      icon={<IconCode />}
                      onClick={() => window.open(paper.urls.code!, "_blank")}
                    >
                      Code
                    </Button>
                  )}
                  <span style={{ flex: 1 }} />
                  {canEdit && (
                    <>
                      <Button
                        size="small"
                        theme="borderless"
                        icon={<IconEdit />}
                        onClick={() => setEditingPaper(paper)}
                      >
                        {t("collection.edit")}
                      </Button>
                      <Button
                        size="small"
                        theme="borderless"
                        type="danger"
                        icon={<IconDelete />}
                        onClick={() => setDeletingPaper(paper)}
                      >
                        {t("collection.remove")}
                      </Button>
                    </>
                  )}
                </div>
                {paper.tags && paper.tags.length > 0 && (
                  <div className="paper-tags">
                    {paper.tags.map((tagItem) => (
                      <Tag key={tagItem} size="small">
                        {tagItem}
                      </Tag>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <PaperEditSheet
        visible={!!editingPaper}
        paper={editingPaper}
        onClose={() => setEditingPaper(null)}
        onSaved={fetchData}
      />
      <CollectionEditSheet
        visible={showCollectionEdit}
        collection={data}
        onClose={() => setShowCollectionEdit(false)}
        onSaved={fetchData}
        onDeleted={() => navigate("/")}
      />
      <AddPapersSheet
        visible={showAddPapers}
        collectionId={id!}
        onClose={() => setShowAddPapers(false)}
        onSuccess={fetchData}
      />

      <Modal
        title={t("collection.removeConfirm")}
        visible={!!deletingPaper}
        onCancel={() => setDeletingPaper(null)}
        onOk={() => {
          if (deletingPaper) {
            handleRemovePaper(deletingPaper.id);
          }
        }}
        okText={t("collection.remove")}
        cancelText={t("home.cancel")}
        okButtonProps={{ type: "danger" }}
      >
        {deletingPaper && (
          <div>
            <Typography.Text>{t("collection.removeHint")}</Typography.Text>
            <Typography.Paragraph strong style={{ marginTop: 12 }}>
              {deletingPaper.title}
            </Typography.Paragraph>
          </div>
        )}
      </Modal>
    </div>
  );
}
