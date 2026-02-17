import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  SideSheet,
  Button,
  Input,
  AutoComplete,
  Typography,
  Toast,
  Select,
  TextArea,
  Tag,
  Spin,
  TagInput,
} from "@douyinfe/semi-ui-19";
import { IconDelete, IconSearch } from "@douyinfe/semi-icons";
import client from "../api/client";
import CollectionDeduplicationModal from "./CollectionDeduplicationModal";
import "../styles/glass.css";
import "../index.css";

const { Title, Text } = Typography;

const isMobile = () => window.innerWidth < 768;

interface CollectionInfo {
  id: string;
  title: string;
  description: string | null;
  visibility: string;
  task_source_display: string | null;
  tags: string[] | null;
}

interface PermissionItem {
  user_id: string;
  username: string;
  display_name: string | null;
  permission: string;
}

interface UserOption {
  user_id: string;
  username: string;
  display_name: string | null;
}

interface Props {
  visible: boolean;
  collection: CollectionInfo | null;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}

export default function CollectionEditSheet({
  visible,
  collection,
  onClose,
  onSaved,
  onDeleted,
}: Props) {
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState("private");
  const [sourceDisplay, setSourceDisplay] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [loadingPerms, setLoadingPerms] = useState(false);
  const [newPermission, setNewPermission] = useState("view");
  const [userSearchResults, setUserSearchResults] = useState<
    { value: string; label: string; user_id: string }[]
  >([]);
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const [showDeduplication, setShowDeduplication] = useState(false);
  const [mobile, setMobile] = useState(isMobile());
  const selectedUserRef = useRef<UserOption | null>(null);
  const justSelectedRef = useRef(false);
  const { t } = useTranslation();
  const fetchPermissions = useCallback(() => {
    if (!collection) return;
    setLoadingPerms(true);
    client
      .get(`/collections/${collection.id}/permissions`)
      .then((res) => setPermissions(res.data))
      .catch(() => {})
      .finally(() => setLoadingPerms(false));
  }, [collection]);

  useEffect(() => {
    if (collection) {
      setTitle(collection.title || "");
      setDescription(collection.description || "");
      setVisibility(collection.visibility || "private");
      setSourceDisplay(collection.task_source_display || "");
      setTags(collection.tags || []);
    }
  }, [collection]);

  useEffect(() => {
    if (visible && collection) fetchPermissions();

    const handleResize = () => setMobile(isMobile());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [visible, collection, fetchPermissions]);

  const handleUserSearch = (query: string) => {
    if (!query || query.length < 1) {
      setUserSearchResults([]);
      return;
    }
    setUserSearchLoading(true);
    client
      .get("/users/search", { params: { q: query } })
      .then((res) => {
        const results = (res.data as UserOption[]).map((u) => ({
          value: u.username,
          label: u.display_name
            ? `${u.display_name} (${u.username})`
            : u.username,
          user_id: u.user_id,
        }));
        setUserSearchResults(results);
      })
      .catch(() => setUserSearchResults([]))
      .finally(() => setUserSearchLoading(false));
  };

  const handleAddPermission = async () => {
    const user = selectedUserRef.current;
    if (!collection || !user) {
      Toast.warning(t("collectionEdit.selectUserFirst"));
      return;
    }
    try {
      await client.post(`/collections/${collection.id}/permissions`, {
        user_id: user.user_id,
        permission: newPermission,
      });
      Toast.success(t("collectionEdit.added"));
      selectedUserRef.current = null;
      setUserSearchResults([]);
      fetchPermissions();
    } catch {
      Toast.error(t("collectionEdit.addFailed"));
    }
  };

  const handleRemovePermission = async (userId: string) => {
    if (!collection) return;
    try {
      await client.delete(
        `/collections/${collection.id}/permissions/${userId}`,
      );
      Toast.success(t("collectionEdit.removed"));
      fetchPermissions();
    } catch {
      Toast.error(t("collectionEdit.removeFailed"));
    }
  };

  const handleSave = async () => {
    if (!collection) return;
    setSaving(true);
    try {
      await client.put(`/collections/${collection.id}`, {
        title,
        description: description || null,
        task_source_display: sourceDisplay || null,
        tags: tags.length > 0 ? tags : null,
      });
      if (visibility !== collection.visibility) {
        await client.put(`/collections/${collection.id}/visibility`, {
          visibility,
        });
      }
      Toast.success(t("collectionEdit.saveSuccess"));
      onSaved();
      onClose();
    } catch {
      Toast.error(t("collectionEdit.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!collection) return;
    if (
      !window.confirm(
        t("collectionEdit.deleteConfirm", { title: collection.title }),
      )
    )
      return;
    try {
      await client.delete(`/collections/${collection.id}`);
      Toast.success(t("collectionEdit.deleted"));
      onDeleted();
    } catch {
      Toast.error(t("collectionEdit.deleteFailed"));
    }
  };

  const footer = (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <Button type="danger" theme="borderless" onClick={handleDelete}>
        {t("collectionEdit.deleteCollection")}
      </Button>
      <div style={{ display: "flex", gap: 8 }}>
        <Button onClick={onClose}>{t("collectionEdit.cancel")}</Button>
        <Button theme="solid" onClick={handleSave} loading={saving}>
          {t("collectionEdit.save")}
        </Button>
      </div>
    </div>
  );

  return (
    <SideSheet
      title={<Title heading={5}>{t("collectionEdit.title")}</Title>}
      visible={visible}
      onCancel={onClose}
      footer={footer}
      size={mobile ? "large" : "small"}
      width={mobile ? "100vw" : undefined}
      headerStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
      bodyStyle={{ borderBottom: "1px solid var(--semi-color-border)" }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label className="form-label">{t("collectionEdit.labelTitle")}</label>
          <Input value={title} onChange={setTitle} />
        </div>
        <div>
          <label className="form-label">
            {t("collectionEdit.labelDescription")}
          </label>
          <TextArea value={description} onChange={setDescription} rows={3} />
        </div>
        <div>
          <label className="form-label">
            {t("collectionEdit.labelVisibility")}
          </label>
          <Select
            value={visibility}
            onChange={(v) => setVisibility(v as string)}
            style={{ width: "100%" }}
          >
            <Select.Option value="private">
              {t("collectionEdit.private")}
            </Select.Option>
            <Select.Option value="shared">
              {t("collectionEdit.shared")}
            </Select.Option>
            <Select.Option value="public">
              {t("collectionEdit.public")}
            </Select.Option>
          </Select>
        </div>
        {visibility === "shared" && (
          <div>
            <label className="form-label">
              {t("collectionEdit.sharedUsers")}
            </label>
            {loadingPerms ? (
              <Spin size="small" />
            ) : (
              <>
                {permissions.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                      marginBottom: 8,
                    }}
                  >
                    {permissions.map((p) => (
                      <div
                        key={p.user_id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <span>
                          <Text>{p.display_name || p.username}</Text>
                          <Tag size="small" style={{ marginLeft: 8 }}>
                            {p.permission === "edit"
                              ? t("collectionEdit.canEdit")
                              : t("collectionEdit.canView")}
                          </Tag>
                        </span>
                        <Button
                          size="small"
                          theme="borderless"
                          type="danger"
                          icon={<IconDelete />}
                          onClick={() => handleRemovePermission(p.user_id)}
                        />
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ display: "flex", gap: 8 }}>
                  <AutoComplete
                    data={userSearchResults}
                    loading={userSearchLoading}
                    onSearch={handleUserSearch}
                    onSelectWithObject
                    onSelect={(item: any) => {
                      selectedUserRef.current = {
                        user_id: item.user_id,
                        username: item.value,
                        display_name: null,
                      };
                      justSelectedRef.current = true;
                    }}
                    onChange={() => {
                      if (justSelectedRef.current) {
                        justSelectedRef.current = false;
                        return;
                      }
                      selectedUserRef.current = null;
                    }}
                    renderSelectedItem={(item: any) => item.value || item}
                    placeholder={t("collectionEdit.searchUser")}
                    prefix={<IconSearch />}
                    style={{ flex: 1 }}
                    emptyContent={
                      <div
                        style={{
                          padding: 8,
                          color: "var(--semi-color-text-2)",
                        }}
                      >
                        {t("collectionEdit.noMatchingUsers")}
                      </div>
                    }
                  />
                  <Select
                    value={newPermission}
                    onChange={(v) => setNewPermission(v as string)}
                    style={{ width: 100 }}
                  >
                    <Select.Option value="view">
                      {t("collectionEdit.view")}
                    </Select.Option>
                    <Select.Option value="edit">
                      {t("collectionEdit.editPerm")}
                    </Select.Option>
                  </Select>
                  <Button onClick={handleAddPermission}>
                    {t("collectionEdit.add")}
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
        <div>
          <label className="form-label">
            {t("collectionEdit.sourceDisplayName")}
          </label>
          <Input
            value={sourceDisplay}
            onChange={setSourceDisplay}
            placeholder={t("collectionEdit.sourceDisplayPlaceholder")}
          />
        </div>
        <div>
          <label className="form-label">{t("collectionEdit.labelTags")}</label>
          <TagInput
            value={tags}
            onChange={(v) => setTags(v as string[])}
            placeholder={t("collectionEdit.tagPlaceholder")}
          />
        </div>
        <div>
          <label className="form-label">
            {t("collectionEdit.deduplication")}
          </label>
          <Button block onClick={() => setShowDeduplication(true)}>
            {t("collectionEdit.findDuplicates")}
          </Button>
        </div>
      </div>
      {collection && (
        <CollectionDeduplicationModal
          visible={showDeduplication}
          collectionId={collection.id}
          onClose={() => setShowDeduplication(false)}
          onSuccess={() => {
            onSaved();
          }}
        />
      )}
    </SideSheet>
  );
}
