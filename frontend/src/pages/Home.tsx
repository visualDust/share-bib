import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Card,
  Tag,
  Empty,
  Spin,
  Input,
  Typography,
  Button,
  Dropdown,
  Toast,
  Modal,
  TagInput,
} from "@douyinfe/semi-ui-19";
import {
  IconSearch,
  IconPlus,
  IconUpload,
  IconList,
  IconTick,
  IconClose,
  IconExternalOpen,
  IconFilter,
  IconSort,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import { usePolling } from "../hooks/usePolling";
import "../styles/glass.css";

const { Text, Paragraph } = Typography;

interface CollectionItem {
  id: string;
  title: string;
  description: string | null;
  created_by: {
    user_id: string;
    username: string;
    display_name: string | null;
  };
  visibility: string;
  task_type: string;
  task_source_display: string | null;
  created_at: string;
  updated_at: string;
  stats: { total: number; accessible: number; no_access: number };
  tags: string[] | null;
}

const visibilityColors: Record<string, string> = {
  private: "grey",
  shared: "blue",
  public: "green",
};

export default function Home() {
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<
    "created" | "updated" | "title" | "count"
  >("updated");
  const navigate = useNavigate();
  const { t } = useTranslation();

  const fetchCollections = useCallback(async () => {
    try {
      const res = await client.get("/collections");
      setCollections(Array.isArray(res.data) ? res.data : []);
    } catch {
      /* handled by interceptor */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);
  usePolling(fetchCollections, 30000);

  // Collect all tags
  const allTags = new Map<string, number>();
  for (const c of collections) {
    for (const tag of c.tags || []) {
      allTags.set(tag, (allTags.get(tag) || 0) + 1);
    }
  }

  const filtered = collections.filter((c) => {
    if (search && !c.title.toLowerCase().includes(search.toLowerCase()))
      return false;
    if (tagFilter && !(c.tags || []).includes(tagFilter)) return false;
    return true;
  });

  // Sort collections
  const sorted = [...filtered].sort((a, b) => {
    switch (sortBy) {
      case "title":
        return a.title.localeCompare(b.title);
      case "count":
        return b.stats.total - a.stats.total;
      case "created":
        return b.created_at.localeCompare(a.created_at);
      case "updated":
      default:
        return b.updated_at.localeCompare(a.updated_at);
    }
  });

  // --- Create collection modal ---
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newId, setNewId] = useState("");
  const [newTags, setNewTags] = useState<string[]>([]);
  const [idStatus, setIdStatus] = useState<
    "idle" | "checking" | "available" | "taken"
  >("idle");
  const [creating, setCreating] = useState(false);
  const idCheckTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkIdAvailability = (id: string) => {
    if (idCheckTimer.current) clearTimeout(idCheckTimer.current);
    if (!id.trim()) {
      setIdStatus("idle");
      return;
    }
    setIdStatus("checking");
    idCheckTimer.current = setTimeout(async () => {
      try {
        const res = await client.get("/collections/check-id", {
          params: { id: id.trim() },
        });
        setIdStatus(res.data.available ? "available" : "taken");
      } catch {
        setIdStatus("idle");
      }
    }, 400);
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) {
      Toast.warning(t("home.titleRequired"));
      return;
    }
    if (newId.trim() && idStatus === "taken") {
      Toast.warning(t("home.idOccupied"));
      return;
    }
    setCreating(true);
    try {
      const res = await client.post("/collections", {
        title: newTitle.trim(),
        id: newId.trim() || undefined,
        task_type: "manual_list",
        tags: newTags.length > 0 ? newTags : undefined,
      });
      setShowCreate(false);
      navigate(`/collections/${res.data.id}`);
    } catch {
      Toast.error(t("home.createFailed"));
    } finally {
      setCreating(false);
    }
  };

  const openCreateModal = () => {
    setNewTitle("");
    setNewId("");
    setNewTags([]);
    setIdStatus("idle");
    setShowCreate(true);
  };

  if (loading)
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );

  return (
    <div>
      <div className="home-header">
        <Typography.Title heading={4} style={{ margin: 0 }}>
          {t("home.myCollections")}
        </Typography.Title>
        <Dropdown
          trigger="click"
          clickToHide
          position="bottomRight"
          render={
            <Dropdown.Menu>
              <Dropdown.Item icon={<IconList />} onClick={openCreateModal}>
                {t("home.emptyCollection")}
              </Dropdown.Item>
              <Dropdown.Item
                icon={<IconUpload />}
                onClick={() => navigate("/import")}
              >
                {t("home.importBibtex")}
              </Dropdown.Item>
            </Dropdown.Menu>
          }
        >
          <span style={{ display: "inline-flex" }}>
            <Button icon={<IconPlus />} theme="solid">
              {t("home.newCollection")}
            </Button>
          </span>
        </Dropdown>
      </div>
      <div className="filter-bar">
        <Input
          prefix={<IconSearch />}
          placeholder={t("home.searchPlaceholder")}
          value={search}
          onChange={setSearch}
          style={{ width: 300, maxWidth: "100%" }}
        />
        {allTags.size > 0 && (
          <Dropdown
            trigger="click"
            showTick
            clickToHide
            position="bottomLeft"
            render={
              <Dropdown.Menu>
                {[...allTags.entries()].map(([tag, count]) => (
                  <Dropdown.Item
                    key={tag}
                    active={tagFilter === tag}
                    onClick={() => setTagFilter(tagFilter === tag ? null : tag)}
                  >
                    {tag} ({count})
                  </Dropdown.Item>
                ))}
              </Dropdown.Menu>
            }
          >
            <span style={{ display: "inline-flex" }}>
              <Button
                icon={<IconFilter />}
                theme={tagFilter ? "light" : "borderless"}
              >
                {t("home.filter")}
              </Button>
            </span>
          </Dropdown>
        )}
        <Dropdown
          trigger="click"
          showTick
          clickToHide
          position="bottomLeft"
          render={
            <Dropdown.Menu>
              <Dropdown.Item
                active={sortBy === "updated"}
                onClick={() => setSortBy("updated")}
              >
                {t("home.sortUpdated")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "created"}
                onClick={() => setSortBy("created")}
              >
                {t("home.sortCreated")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "title"}
                onClick={() => setSortBy("title")}
              >
                {t("home.sortTitle")}
              </Dropdown.Item>
              <Dropdown.Item
                active={sortBy === "count"}
                onClick={() => setSortBy("count")}
              >
                {t("home.sortCount")}
              </Dropdown.Item>
            </Dropdown.Menu>
          }
        >
          <span style={{ display: "inline-flex" }}>
            <Button icon={<IconSort />} theme="borderless">
              {t("home.sort")}
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
      {sorted.length === 0 ? (
        <Empty
          description={t("home.noCollections")}
          style={{ marginTop: 80 }}
        />
      ) : (
        <div className="collection-grid">
          {sorted.map((c) => (
            <div key={c.id} onClick={() => navigate(`/collections/${c.id}`)}>
              <Card
                className="collection-card glass-card"
                style={{ cursor: "pointer" }}
              >
                <div className="collection-card-header">
                  <Text strong style={{ fontSize: 16 }}>
                    {c.title}
                  </Text>
                  <Tag
                    color={(visibilityColors[c.visibility] || "grey") as any}
                    size="small"
                  >
                    {c.visibility}
                  </Tag>
                </div>
                {c.description && (
                  <Paragraph
                    ellipsis={{ rows: 2 }}
                    style={{ color: "var(--semi-color-text-2)", marginTop: 4 }}
                  >
                    {c.description}
                  </Paragraph>
                )}
                {c.tags && c.tags.length > 0 && (
                  <div className="collection-card-meta">
                    {c.tags.map((tag) => (
                      <Tag key={tag} size="small" color="light-blue">
                        {tag}
                      </Tag>
                    ))}
                  </div>
                )}
                <div className="collection-card-footer">
                  <Text type="tertiary" size="small">
                    {t("home.paperStats", {
                      total: c.stats.total,
                      accessible: c.stats.accessible,
                    })}
                  </Text>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <Text type="tertiary" size="small">
                      {new Date(c.created_at).toLocaleDateString()}
                    </Text>
                    <Button
                      icon={<IconExternalOpen />}
                      theme="borderless"
                      size="small"
                      type="tertiary"
                      style={{ padding: 2, height: "auto" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(`/collections/${c.id}`, "_blank");
                      }}
                    />
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}

      <Modal
        title={t("home.createTitle")}
        visible={showCreate}
        onCancel={() => setShowCreate(false)}
        onOk={handleCreate}
        okText={t("home.create")}
        cancelText={t("home.cancel")}
        confirmLoading={creating}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label className="form-label">{t("home.labelTitle")}</label>
            <Input
              value={newTitle}
              onChange={setNewTitle}
              placeholder={t("home.collectionNamePlaceholder")}
              autoFocus
            />
          </div>
          <div>
            <label className="form-label">{t("home.customId")}</label>
            <Input
              value={newId}
              onChange={(v) => {
                setNewId(v);
                checkIdAvailability(v);
              }}
              placeholder={t("home.autoGenerateId")}
              suffix={
                idStatus === "checking" ? (
                  <Spin size="small" />
                ) : idStatus === "available" ? (
                  <IconTick style={{ color: "var(--semi-color-success)" }} />
                ) : idStatus === "taken" ? (
                  <IconClose style={{ color: "var(--semi-color-danger)" }} />
                ) : null
              }
            />
            {idStatus === "taken" && (
              <Text type="danger" size="small">
                {t("home.idTaken")}
              </Text>
            )}
          </div>
          <div>
            <label className="form-label">{t("home.labelTags")}</label>
            <TagInput
              value={newTags}
              onChange={(v) => setNewTags(v as string[])}
              placeholder={t("home.tagPlaceholder")}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
