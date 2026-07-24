import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Tag,
  Card,
  Empty,
  Spin,
  Button,
  Modal,
  Form,
  Toast,
} from "@douyinfe/semi-ui-19";
import {
  IconArrowLeft,
  IconEdit,
  IconExternalOpen,
  IconKey,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import ProfileEditModal, {
  type EditableProfile,
} from "../components/ProfileEditModal";
import "../styles/surfaces.css";

const { Text, Paragraph, Title } = Typography;

interface CollectionItem {
  id: string;
  title: string;
  description: string | null;
  visibility: string;
  task_type: string;
  task_source_display: string | null;
  created_at: string;
  updated_at: string;
  stats: { total: number; accessible: number; no_access: number };
  tags: string[] | null;
}

interface UserProfile {
  user: {
    username: string;
    display_name: string | null;
    created_at: string;
  };
  collections: CollectionItem[];
}

const visibilityColors: Record<string, string> = {
  private: "grey",
  shared: "blue",
  public: "green",
  public_editable: "green",
};

const visibilityLabels: Record<string, string> = {
  private: "collectionEdit.private",
  shared: "collectionEdit.shared",
  public: "collectionEdit.public",
  public_editable: "collectionEdit.publicEditable",
};

export default function UserProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [data, setData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<EditableProfile | null>(null);
  const [profileVisible, setProfileVisible] = useState(false);
  const [pwdVisible, setPwdVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const pwdFormRef = useRef<any>(null);

  useEffect(() => {
    client
      .get("/auth/me")
      .then((res) => setCurrentUser(res.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!username) return;
    client
      .get(`/users/${username}/profile`)
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [username]);

  if (loading)
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );
  if (!data)
    return (
      <Empty
        description={t("userProfile.notFound")}
        style={{ marginTop: 80 }}
      />
    );

  const displayName = data.user.display_name || data.user.username;
  const isOwnProfile = currentUser?.username === data.user.username;

  const handleChangePassword = async (values: {
    old_password: string;
    new_password: string;
  }) => {
    setSubmitting(true);
    try {
      await client.put("/users/me/change-password", values);
      Toast.success(t("userProfile.passwordChanged"));
      setPwdVisible(false);
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("userProfile.changeFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="profile-page">
      <Button
        className="profile-back"
        icon={<IconArrowLeft />}
        theme="borderless"
        onClick={() => navigate("/")}
      >
        {t("userProfile.back")}
      </Button>

      <header className="profile-header">
        <div className="profile-identity">
          <Title heading={3}>{displayName}</Title>
          <div className="profile-meta">
            <Text type="tertiary">@{data.user.username}</Text>
            {isOwnProfile && currentUser?.email && (
              <>
                <span aria-hidden="true" />
                <Text type="tertiary">{currentUser.email}</Text>
              </>
            )}
            <span aria-hidden="true" />
            <Text type="tertiary">
              {t("userProfile.joinedAt", {
                date: new Date(data.user.created_at).toLocaleDateString(),
              })}
            </Text>
          </div>
        </div>
        {isOwnProfile && (
          <div className="profile-account-actions">
            <Button
              icon={<IconEdit />}
              theme="light"
              onClick={() => setProfileVisible(true)}
            >
              {t("settings.editProfile")}
            </Button>
            <Button
              icon={<IconKey />}
              theme="borderless"
              type="tertiary"
              onClick={() => setPwdVisible(true)}
            >
              {t("userProfile.changePassword")}
            </Button>
          </div>
        )}
      </header>

      <div className="profile-section-heading">
        <Title heading={5}>
          {t("userProfile.collections", { count: data.collections.length })}
        </Title>
      </div>

      {data.collections.length === 0 ? (
        <Empty description={t("userProfile.noCollections")} />
      ) : (
        <div className="collection-grid collection-index">
          {data.collections.map((c) => (
            <div key={c.id} onClick={() => navigate(`/collections/${c.id}`)}>
              <Card
                className="collection-card collection-index-card surface-card"
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
                    {t(visibilityLabels[c.visibility] || c.visibility)}
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
                    {t("userProfile.paperCount", { count: c.stats.total })}
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
                      aria-label={t("userProfile.openCollection", {
                        title: c.title,
                      })}
                      title={t("userProfile.openCollection", {
                        title: c.title,
                      })}
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

      <ProfileEditModal
        visible={profileVisible}
        user={currentUser}
        onClose={() => setProfileVisible(false)}
        onUpdated={(profile) => {
          setCurrentUser(profile);
          setData((current) =>
            current
              ? {
                  ...current,
                  user: {
                    ...current.user,
                    username: profile.username,
                    display_name: profile.display_name,
                  },
                }
              : current,
          );
          if (profile.username !== username) {
            navigate(`/user/${profile.username}`, { replace: true });
          }
        }}
      />

      <Modal
        className="profile-password-dialog"
        title={t("userProfile.changePasswordTitle")}
        visible={pwdVisible}
        onCancel={() => setPwdVisible(false)}
        width={480}
        footer={
          <div className="profile-dialog-actions">
            <Button theme="borderless" onClick={() => setPwdVisible(false)}>
              {t("userProfile.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={submitting}
              onClick={() => pwdFormRef.current?.formApi?.submitForm()}
            >
              {t("userProfile.confirmChange")}
            </Button>
          </div>
        }
      >
        <Form ref={pwdFormRef} onSubmit={handleChangePassword}>
          <Form.Input
            field="old_password"
            label={t("userProfile.currentPassword")}
            mode="password"
            rules={[
              {
                required: true,
                message: t("userProfile.currentPasswordRequired"),
              },
            ]}
          />
          <Form.Input
            field="new_password"
            label={t("userProfile.newPassword")}
            mode="password"
            rules={[
              { required: true, message: t("userProfile.newPasswordRequired") },
            ]}
          />
        </Form>
      </Modal>
    </div>
  );
}
