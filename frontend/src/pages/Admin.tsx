import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Button,
  Modal,
  Form,
  Toast,
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
  IconKey,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import "../styles/surfaces.css";

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
  const [userQuery, setUserQuery] = useState("");
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

  const filteredUsers = useMemo(() => {
    const query = userQuery.trim().toLowerCase();
    if (!query) return users;
    return users.filter((user) =>
      [user.username, user.display_name, user.email]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query)),
    );
  }, [userQuery, users]);

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
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <Title heading={3}>{t("admin.title")}</Title>
          <Text className="admin-page-description">{t("admin.subtitle")}</Text>
        </div>
        <div className="admin-counts" aria-label={t("admin.summaryLabel")}>
          <span>
            <strong>{users.length}</strong> {t("admin.totalUsers")}
          </span>
          <span>
            <strong>{users.filter((user) => user.is_active).length}</strong>{" "}
            {t("admin.activeUsers")}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="admin-loading">
          <Spin size="large" />
        </div>
      ) : users.length === 0 ? (
        <Empty description={t("admin.noUsers")} style={{ marginTop: 80 }} />
      ) : (
        <section className="admin-directory" aria-labelledby="user-directory">
          <div className="admin-directory-toolbar">
            <div>
              <Title id="user-directory" heading={5}>
                {t("admin.directory")}
              </Title>
              <Text>{t("admin.directoryCount", { count: users.length })}</Text>
            </div>
            <div className="admin-directory-actions">
              <Input
                prefix={<IconSearch />}
                value={userQuery}
                onChange={setUserQuery}
                showClear
                placeholder={t("admin.searchUsers")}
                aria-label={t("admin.searchUsers")}
              />
              <Button
                icon={<IconPlus />}
                theme="solid"
                onClick={() => setCreateVisible(true)}
              >
                {t("admin.addUser")}
              </Button>
            </div>
          </div>

          {filteredUsers.length === 0 ? (
            <div className="admin-no-results">
              <Empty description={t("admin.noMatchingUsers")} />
            </div>
          ) : (
            <div className="admin-user-list">
              {filteredUsers.map((u) => (
                <article key={u.id} className="admin-user-row">
                  <div className="admin-user-identity">
                    <div className="admin-user-avatar" aria-hidden="true">
                      {(u.display_name || u.username).charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <strong>{u.display_name || u.username}</strong>
                      <span>
                        {u.display_name && u.display_name !== u.username
                          ? `@${u.username}`
                          : u.email || t("admin.noEmail")}
                      </span>
                    </div>
                  </div>
                  <div className="admin-user-detail">
                    <span>{t("admin.email")}</span>
                    <strong>{u.email || t("admin.noEmail")}</strong>
                  </div>
                  <div className="admin-user-detail">
                    <span>{t("admin.joined")}</span>
                    <strong>
                      {new Date(u.created_at).toLocaleDateString()}
                    </strong>
                  </div>
                  <span
                    className={`admin-user-status ${u.is_active ? "is-active" : "is-inactive"}`}
                  >
                    <i aria-hidden="true" />
                    {u.is_active ? t("admin.active") : t("admin.inactive")}
                  </span>
                  <div className="admin-user-actions">
                    <Button
                      size="small"
                      theme="light"
                      type="tertiary"
                      icon={<IconEdit />}
                      onClick={() => openEditModal(u)}
                    >
                      {t("admin.edit")}
                    </Button>
                    <Button
                      size="small"
                      theme="borderless"
                      type="tertiary"
                      icon={<IconKey />}
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
                    <Button
                      size="small"
                      theme="borderless"
                      type="danger"
                      icon={<IconDelete />}
                      aria-label={`${t("admin.delete")} ${u.username}`}
                      title={`${t("admin.delete")} ${u.username}`}
                      onClick={() => openDeleteModal(u.id)}
                    />
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      <Modal
        className="admin-dialog"
        title={t("admin.addUserTitle")}
        visible={createVisible}
        onCancel={() => setCreateVisible(false)}
        footer={
          <div className="admin-dialog-actions">
            <Button theme="borderless" onClick={() => setCreateVisible(false)}>
              {t("admin.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={submitting}
              onClick={() => createFormRef.current?.formApi?.submitForm()}
            >
              {t("admin.create")}
            </Button>
          </div>
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
        className="admin-dialog"
        title={t("admin.resetPasswordTitle")}
        visible={resetVisible}
        onCancel={() => {
          setResetVisible(false);
          setResetUserId(null);
        }}
        footer={
          <div className="admin-dialog-actions">
            <Button theme="borderless" onClick={() => setResetVisible(false)}>
              {t("admin.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={submitting}
              onClick={() => resetFormRef.current?.formApi?.submitForm()}
            >
              {t("admin.confirmReset")}
            </Button>
          </div>
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
        className="admin-dialog"
        title={t("admin.editUserTitle")}
        visible={editVisible}
        onCancel={() => {
          setEditVisible(false);
          setEditUser(null);
        }}
        footer={
          <div className="admin-dialog-actions">
            <Button theme="borderless" onClick={() => setEditVisible(false)}>
              {t("admin.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={submitting}
              onClick={handleEditSubmit}
            >
              {t("admin.save")}
            </Button>
          </div>
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
        className="admin-dialog admin-delete-dialog"
        title={t("admin.deleteUserTitle")}
        visible={deleteVisible}
        onCancel={() => {
          setDeleteVisible(false);
          setDeleteUserId(null);
        }}
        footer={
          <div className="admin-dialog-actions">
            <Button theme="borderless" onClick={() => setDeleteVisible(false)}>
              {t("admin.cancel")}
            </Button>
            <Button
              theme="solid"
              type="danger"
              loading={submitting}
              onClick={handleDelete}
            >
              {t("admin.confirmDelete")}
            </Button>
          </div>
        }
      >
        <div className="admin-delete-options">
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
