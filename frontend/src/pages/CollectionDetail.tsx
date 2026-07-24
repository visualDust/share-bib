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
  IconListView,
  IconMenu,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import PaperEditSheet from "../components/PaperEditSheet";
import CollectionEditSheet from "../components/CollectionEditSheet";
import AddPapersSheet from "../components/AddPapersSheet";
import "../styles/surfaces.css";

const { Paragraph, Title } = Typography;

const isMobile = () => window.innerWidth < 768;

type PaperLayout = "comfortable" | "compact";

const getInitialPaperLayout = (): PaperLayout => {
  if (typeof window === "undefined") return "comfortable";
  const saved = window.localStorage.getItem("sharebib-paper-layout");
  return saved === "compact" ? "compact" : "comfortable";
};

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
  const [paperLayout, setPaperLayout] = useState<PaperLayout>(
    getInitialPaperLayout,
  );
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

  const handlePaperLayoutChange = (nextLayout: PaperLayout) => {
    setPaperLayout(nextLayout);
    window.localStorage.setItem("sharebib-paper-layout", nextLayout);
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
    <div className="collection-detail-page">
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
          aria-label={isLoggedIn ? t("collection.back") : t("collection.login")}
          title={isLoggedIn ? t("collection.back") : t("collection.login")}
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
              aria-label={t("collection.exportBibtex")}
              title={t("collection.exportBibtex")}
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
                aria-label={t("collection.addPapers")}
                title={t("collection.addPapers")}
                onClick={() => setShowAddPapers(true)}
                style={
                  mobile ? { minWidth: "auto", padding: "8px 12px" } : undefined
                }
              >
                {mobile ? null : t("collection.addPapers")}
              </Button>
              <Button
                icon={<IconSetting />}
                theme="light"
                type="tertiary"
                aria-label={t("collection.editCollection")}
                title={t("collection.editCollection")}
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
        <section
          className={`data-list paper-index${paperLayout === "compact" ? " is-compact" : ""}`}
        >
          <div className="data-list-header">
            <span>
              {t("collection.paperList", { count: sortedPapers.length })}
            </span>
            <div
              className="layout-toggle paper-layout-toggle"
              role="group"
              aria-label={t("collection.layout")}
            >
              <button
                type="button"
                className={paperLayout === "comfortable" ? "active" : ""}
                onClick={() => handlePaperLayoutChange("comfortable")}
                aria-label={t("collection.comfortableView")}
                title={t("collection.comfortableView")}
                aria-pressed={paperLayout === "comfortable"}
              >
                <IconListView aria-hidden="true" />
              </button>
              <button
                type="button"
                className={paperLayout === "compact" ? "active" : ""}
                onClick={() => handlePaperLayoutChange("compact")}
                aria-label={t("collection.compactView")}
                title={t("collection.compactView")}
                aria-pressed={paperLayout === "compact"}
              >
                <IconMenu aria-hidden="true" />
              </button>
            </div>
          </div>
          <div className="data-list-body">
            {sortedPapers.map((paper, index) => {
              const primaryUrl = paper.urls.arxiv || paper.urls.pdf;
              const venue =
                paper.venue && paper.venue.toLowerCase() !== "unknown"
                  ? paper.venue
                  : null;

              return (
                <article key={paper.id} className="paper-item paper-record">
                  <div className="paper-record-number" aria-hidden="true">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div className="paper-record-content">
                    <header className="paper-record-header">
                      <div className="paper-record-heading">
                        <div className="paper-kicker">
                          {paper.year && <span>{paper.year}</span>}
                          {venue && <span title={venue}>{venue}</span>}
                          <span>{sourceTagLabel(paper.group_tag)}</span>
                        </div>
                        <h3 className="paper-record-title">
                          {primaryUrl ? (
                            <a
                              href={primaryUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {paper.title}
                            </a>
                          ) : (
                            paper.title
                          )}
                        </h3>
                      </div>
                      <div
                        className={`paper-status${paper.status === "accessible" ? " is-accessible" : " is-unavailable"}`}
                      >
                        <span aria-hidden="true" />
                        {paper.status === "accessible"
                          ? t("collection.statusAccessible")
                          : t("collection.statusNoAccess")}
                      </div>
                    </header>

                    {(paper.authors || []).length > 0 && (
                      <p className="paper-authors">
                        {(paper.authors || []).join(", ")}
                      </p>
                    )}

                    {paper.summary && (
                      <Paragraph
                        ellipsis={{
                          rows: mobile ? 4 : 2,
                          expandable: !mobile,
                        }}
                        className="paper-summary"
                      >
                        {paper.summary}
                      </Paragraph>
                    )}

                    <footer className="paper-record-footer">
                      <div className="paper-resources">
                        {paper.urls.arxiv && (
                          <a
                            href={paper.urls.arxiv}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="paper-resource-link"
                          >
                            <IconLink aria-hidden="true" />
                            arXiv
                          </a>
                        )}
                        {paper.urls.pdf && (
                          <a
                            href={paper.urls.pdf}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="paper-resource-link"
                          >
                            PDF
                          </a>
                        )}
                        {paper.urls.code && (
                          <a
                            href={paper.urls.code}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="paper-resource-link"
                          >
                            <IconCode aria-hidden="true" />
                            Code
                          </a>
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

                      {canEdit && (
                        <div className="paper-management">
                          <Button
                            size="small"
                            theme="borderless"
                            icon={<IconEdit />}
                            aria-label={t("collection.edit")}
                            title={t("collection.edit")}
                            onClick={() => setEditingPaper(paper)}
                          >
                            {paperLayout === "comfortable"
                              ? t("collection.edit")
                              : null}
                          </Button>
                          <Button
                            size="small"
                            theme="borderless"
                            type="danger"
                            icon={<IconDelete />}
                            aria-label={t("collection.remove")}
                            title={t("collection.remove")}
                            onClick={() => setDeletingPaper(paper)}
                          >
                            {paperLayout === "comfortable"
                              ? t("collection.remove")
                              : null}
                          </Button>
                        </div>
                      )}
                    </footer>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <PaperEditSheet
        visible={!!editingPaper}
        paper={editingPaper}
        collectionId={id!}
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
