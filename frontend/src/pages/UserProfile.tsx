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
} from "@douyinfe/semi-icons";
import client from "../api/client";
import "../styles/glass.css";

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
};

export default function UserProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [data, setData] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentUsername, setCurrentUsername] = useState<string | null>(null);
  const [pwdVisible, setPwdVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const pwdFormRef = useRef<any>(null);

  useEffect(() => {
    client
      .get("/auth/me")
      .then((res) => setCurrentUsername(res.data.username))
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
  const isOwnProfile = currentUsername === data.user.username;

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
    <div>
      <Button
        icon={<IconArrowLeft />}
        theme="borderless"
        onClick={() => navigate("/")}
        style={{ marginBottom: 16 }}
      >
        {t("userProfile.back")}
      </Button>

      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Title heading={3}>{displayName}</Title>
          {isOwnProfile && (
            <Button
              size="small"
              icon={<IconEdit />}
              theme="light"
              onClick={() => setPwdVisible(true)}
            >
              {t("userProfile.changePassword")}
            </Button>
          )}
        </div>
        <Text type="tertiary">@{data.user.username}</Text>
        <Text type="tertiary" style={{ marginLeft: 12 }}>
          {t("userProfile.joinedAt", {
            date: new Date(data.user.created_at).toLocaleDateString(),
          })}
        </Text>
      </div>

      <Title heading={5} style={{ marginBottom: 16 }}>
        {t("userProfile.collections", { count: data.collections.length })}
      </Title>

      {data.collections.length === 0 ? (
        <Empty description={t("userProfile.noCollections")} />
      ) : (
        <div className="collection-grid">
          {data.collections.map((c) => (
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
        title={t("userProfile.changePasswordTitle")}
        visible={pwdVisible}
        onCancel={() => setPwdVisible(false)}
        footer={
          <Button
            theme="solid"
            loading={submitting}
            onClick={() => pwdFormRef.current?.formApi?.submitForm()}
          >
            {t("userProfile.confirmChange")}
          </Button>
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
