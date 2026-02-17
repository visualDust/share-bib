import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Button,
  Modal,
  Form,
  Toast,
  Tag,
  Typography,
  Spin,
  Empty,
  AutoComplete,
  RadioGroup,
  Radio,
  Input,
} from "@douyinfe/semi-ui-19";
import {
  IconPlus,
  IconDelete,
  IconEdit,
  IconSearch,
  IconTick,
  IconClose,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import "../styles/glass.css";

const { Title, Text } = Typography;

interface AdminUser {
  id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  is_active: boolean;
  created_at: string;
}

export default function Admin() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [resetVisible, setResetVisible] = useState(false);
  const [resetUserId, setResetUserId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const createFormRef = useRef<any>(null);
  const resetFormRef = useRef<any>(null);
  const [deleteVisible, setDeleteVisible] = useState(false);
  const [deleteUserId, setDeleteUserId] = useState<string | null>(null);
  const [deleteMode, setDeleteMode] = useState<"transfer" | "delete">(
    "transfer",
  );
  const [userSearchResults, setUserSearchResults] = useState<
    { value: string; label: string; user_id: string }[]
  >([]);
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const transferUserRef = useRef<{ user_id: string; username: string } | null>(
    null,
  );
  const justSelectedRef = useRef(false);
  const [editVisible, setEditVisible] = useState(false);
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState({
    username: "",
    email: "",
    display_name: "",
  });
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const checkTimerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>(
    {},
  );

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await client.get("/admin/users");
      setUsers(res.data);
    } catch {
      Toast.error(t("admin.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    client
      .get("/auth/me")
      .then((res) => {
        if (res.data.is_admin) {
          setIsAdmin(true);
          fetchUsers();
        } else {
          navigate("/");
        }
      })
      .catch(() => navigate("/login"));
  }, [navigate, fetchUsers]);

  const handleCreate = async (values: Record<string, string>) => {
    setSubmitting(true);
    try {
      await client.post("/admin/users", values);
      Toast.success(t("admin.userCreated"));
      setCreateVisible(false);
      fetchUsers();
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("admin.createFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPassword = async (values: { new_password: string }) => {
    if (!resetUserId) return;
    setSubmitting(true);
    try {
      await client.put(`/admin/users/${resetUserId}/reset-password`, values);
      Toast.success(t("admin.passwordReset"));
      setResetVisible(false);
      setResetUserId(null);
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("admin.resetFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (userId: string) => {
    try {
      await client.put(`/admin/users/${userId}/toggle-active`);
      fetchUsers();
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("admin.operationFailed"));
    }
  };

  const openEditModal = (u: AdminUser) => {
    setEditUser(u);
    setEditForm({
      username: u.username,
      email: u.email || "",
      display_name: u.display_name || "",
    });
    setEditErrors({});
    setEditVisible(true);
  };

  const checkField = (field: string, value: string) => {
    if (checkTimerRef.current[field])
      clearTimeout(checkTimerRef.current[field]);
    if (!value) {
      setEditErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    if (field === "username" && value === editUser?.username) {
      setEditErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    if (field === "email" && value === (editUser?.email || "")) {
      setEditErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    checkTimerRef.current[field] = setTimeout(async () => {
      try {
        const res = await client.get("/admin/users/check", {
          params: { field, value, exclude_id: editUser?.id },
        });
        setEditErrors((prev) => {
          const n = { ...prev };
          if (res.data.available) {
            delete n[field];
          } else {
            n[field] = t("admin.alreadyTaken");
          }
          return n;
        });
      } catch {
        /* ignore */
      }
    }, 300);
  };

  const handleEditField = (field: string, value: string) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
    if (field === "username" || field === "email") checkField(field, value);
  };

  const handleEditSubmit = async () => {
    if (!editUser) return;
    if (Object.keys(editErrors).length > 0) {
      Toast.warning(t("admin.fixConflicts"));
      return;
    }
    if (!editForm.username) {
      Toast.warning(t("admin.usernameEmpty"));
      return;
    }
    setSubmitting(true);
    try {
      await client.put(`/admin/users/${editUser.id}`, {
        username: editForm.username,
        email: editForm.email || null,
        display_name: editForm.display_name || null,
      });
      Toast.success(t("admin.userUpdated"));
      setEditVisible(false);
      setEditUser(null);
      fetchUsers();
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("admin.updateFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleUserSearch = (query: string) => {
    if (!query || query.length < 1) {
      setUserSearchResults([]);
      return;
    }
    setUserSearchLoading(true);
    client
      .get("/admin/users/search", {
        params: { q: query, exclude: deleteUserId },
      })
      .then((res) => {
        const results = (
          res.data as {
            user_id: string;
            username: string;
            display_name: string | null;
          }[]
        ).map((u) => ({
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

  const openDeleteModal = (userId: string) => {
    setDeleteUserId(userId);
    setDeleteMode("transfer");
    transferUserRef.current = null;
    setUserSearchResults([]);
    setDeleteVisible(true);
  };

  const handleDelete = async () => {
    if (!deleteUserId) return;
    if (deleteMode === "transfer" && !transferUserRef.current) {
      Toast.warning(t("admin.selectTransferRequired"));
      return;
    }
    setSubmitting(true);
    try {
      await client.delete(`/admin/users/${deleteUserId}`, {
        data: {
          mode: deleteMode,
          transfer_to:
            deleteMode === "transfer" ? transferUserRef.current?.user_id : null,
        },
      });
      Toast.success(t("admin.userDeleted"));
      setDeleteVisible(false);
      setDeleteUserId(null);
      fetchUsers();
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("admin.deleteFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isAdmin)
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );

  return (
    <div>
      <div className="home-header">
        <Title heading={4} style={{ margin: 0 }}>
          {t("admin.title")}
        </Title>
        <Button
          icon={<IconPlus />}
          theme="solid"
          onClick={() => setCreateVisible(true)}
        >
          {t("admin.addUser")}
        </Button>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "80px auto" }} />
      ) : users.length === 0 ? (
        <Empty description={t("admin.noUsers")} style={{ marginTop: 80 }} />
      ) : (
        <div className="glass-table-wrapper">
          <div className="glass-table-header">
            <span>{t("admin.userList", { count: users.length })}</span>
          </div>
          <div className="glass-table-body">
            {users.map((u) => (
              <div key={u.id} className="paper-item">
                <div className="paper-title-row">
                  <div style={{ flex: 1 }}>
                    <Text strong style={{ fontSize: 15 }}>
                      {u.username}
                    </Text>
                    {u.display_name && u.display_name !== u.username && (
                      <Text type="tertiary" style={{ marginLeft: 8 }}>
                        {u.display_name}
                      </Text>
                    )}
                    <div className="paper-meta">
                      {u.email || t("admin.noEmail")} ·{" "}
                      {new Date(u.created_at).toLocaleDateString()}
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
                    <Tag size="small" color={u.is_active ? "green" : "red"}>
                      {u.is_active ? t("admin.active") : t("admin.inactive")}
                    </Tag>
                  </div>
                </div>
                <div className="paper-links">
                  <Button
                    size="small"
                    theme="borderless"
                    icon={<IconEdit />}
                    onClick={() => openEditModal(u)}
                  >
                    {t("admin.edit")}
                  </Button>
                  <Button
                    size="small"
                    theme="borderless"
                    onClick={() => {
                      setResetUserId(u.id);
                      setResetVisible(true);
                    }}
                  >
                    {t("admin.resetPassword")}
                  </Button>
                  <Button
                    size="small"
                    theme="borderless"
                    type={u.is_active ? "warning" : "primary"}
                    onClick={() => handleToggleActive(u.id)}
                  >
                    {u.is_active ? t("admin.disable") : t("admin.enable")}
                  </Button>
                  <span style={{ flex: 1 }} />
                  <Button
                    size="small"
                    theme="borderless"
                    type="danger"
                    icon={<IconDelete />}
                    onClick={() => openDeleteModal(u.id)}
                  >
                    {t("admin.delete")}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal
        title={t("admin.addUserTitle")}
        visible={createVisible}
        onCancel={() => setCreateVisible(false)}
        footer={
          <Button
            theme="solid"
            loading={submitting}
            onClick={() => createFormRef.current?.formApi?.submitForm()}
          >
            {t("admin.create")}
          </Button>
        }
      >
        <Form ref={createFormRef} onSubmit={handleCreate}>
          <Form.Input
            field="username"
            label={t("admin.username")}
            rules={[{ required: true, message: t("admin.usernameRequired") }]}
          />
          <Form.Input
            field="password"
            label={t("admin.password")}
            mode="password"
            rules={[{ required: true, message: t("admin.passwordRequired") }]}
          />
          <Form.Input field="email" label={t("admin.email")} />
          <Form.Input field="display_name" label={t("admin.displayName")} />
        </Form>
      </Modal>

      <Modal
        title={t("admin.resetPasswordTitle")}
        visible={resetVisible}
        onCancel={() => {
          setResetVisible(false);
          setResetUserId(null);
        }}
        footer={
          <Button
            theme="solid"
            loading={submitting}
            onClick={() => resetFormRef.current?.formApi?.submitForm()}
          >
            {t("admin.confirmReset")}
          </Button>
        }
      >
        <Form ref={resetFormRef} onSubmit={handleResetPassword}>
          <Form.Input
            field="new_password"
            label={t("admin.newPassword")}
            mode="password"
            rules={[
              { required: true, message: t("admin.newPasswordRequired") },
            ]}
          />
        </Form>
      </Modal>

      <Modal
        title={t("admin.editUserTitle")}
        visible={editVisible}
        onCancel={() => {
          setEditVisible(false);
          setEditUser(null);
        }}
        footer={
          <Button theme="solid" loading={submitting} onClick={handleEditSubmit}>
            {t("admin.save")}
          </Button>
        }
      >
        {editUser && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div className="form-label">{t("admin.username")}</div>
              <Input
                value={editForm.username}
                onChange={(v) => handleEditField("username", v)}
                suffix={
                  editErrors.username ? (
                    <IconClose style={{ color: "var(--semi-color-danger)" }} />
                  ) : editForm.username &&
                    editForm.username !== editUser.username ? (
                    <IconTick style={{ color: "var(--semi-color-success)" }} />
                  ) : null
                }
              />
              {editErrors.username && (
                <div
                  style={{
                    color: "var(--semi-color-danger)",
                    fontSize: 12,
                    marginTop: 2,
                  }}
                >
                  {editErrors.username}
                </div>
              )}
            </div>
            <div>
              <div className="form-label">{t("admin.email")}</div>
              <Input
                value={editForm.email}
                onChange={(v) => handleEditField("email", v)}
                suffix={
                  editErrors.email ? (
                    <IconClose style={{ color: "var(--semi-color-danger)" }} />
                  ) : editForm.email &&
                    editForm.email !== (editUser.email || "") ? (
                    <IconTick style={{ color: "var(--semi-color-success)" }} />
                  ) : null
                }
              />
              {editErrors.email && (
                <div
                  style={{
                    color: "var(--semi-color-danger)",
                    fontSize: 12,
                    marginTop: 2,
                  }}
                >
                  {editErrors.email}
                </div>
              )}
            </div>
            <div>
              <div className="form-label">{t("admin.displayName")}</div>
              <Input
                value={editForm.display_name}
                onChange={(v) => handleEditField("display_name", v)}
              />
            </div>
          </div>
        )}
      </Modal>

      <Modal
        title={t("admin.deleteUserTitle")}
        visible={deleteVisible}
        onCancel={() => {
          setDeleteVisible(false);
          setDeleteUserId(null);
        }}
        footer={
          <Button
            theme="solid"
            type="danger"
            loading={submitting}
            onClick={handleDelete}
          >
            {t("admin.confirmDelete")}
          </Button>
        }
      >
        <div style={{ marginBottom: 16 }}>
          <RadioGroup
            value={deleteMode}
            onChange={(e) => {
              setDeleteMode(e.target.value as "transfer" | "delete");
              transferUserRef.current = null;
            }}
            direction="vertical"
          >
            <Radio value="transfer">{t("admin.transferCollections")}</Radio>
            <Radio value="delete">{t("admin.deleteAllData")}</Radio>
          </RadioGroup>
        </div>
        {deleteMode === "transfer" && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
              {t("admin.selectTransferUser")}
            </div>
            <AutoComplete
              data={userSearchResults}
              loading={userSearchLoading}
              onSearch={handleUserSearch}
              onSelectWithObject
              onSelect={(item: any) => {
                transferUserRef.current = {
                  user_id: item.user_id,
                  username: item.value,
                };
                justSelectedRef.current = true;
              }}
              onChange={() => {
                if (justSelectedRef.current) {
                  justSelectedRef.current = false;
                  return;
                }
                transferUserRef.current = null;
              }}
              renderSelectedItem={(item: any) => item.value || item}
              placeholder={t("admin.searchUsername")}
              prefix={<IconSearch />}
              style={{ width: "100%" }}
              emptyContent={
                <div style={{ padding: 8, color: "var(--semi-color-text-2)" }}>
                  {t("admin.noMatchingUsers")}
                </div>
              }
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
