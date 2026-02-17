import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, Form, Button, Toast, Typography } from "@douyinfe/semi-ui-19";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useSystemStatus } from "../App";
import client from "../api/client";
import "../styles/glass.css";

const { Text } = Typography;

export default function Setup() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { status, setStatus } = useSystemStatus();

  const isOAuth = status?.auth_type === "oauth" && status?.oauth_configured;

  const handleSubmit = async (values: {
    username: string;
    password: string;
    confirmPassword: string;
    display_name?: string;
    email?: string;
  }) => {
    if (values.password !== values.confirmPassword) {
      Toast.error(t("setup.passwordMismatch"));
      return;
    }
    setLoading(true);
    try {
      const res = await client.post("/system/setup", {
        username: values.username,
        password: values.password,
        display_name: values.display_name || undefined,
        email: values.email || undefined,
      });
      localStorage.setItem("token", res.data.access_token);
      setStatus((prev) => (prev ? { ...prev, initialized: true } : prev));
      Toast.success(t("setup.success"));
      navigate("/");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      Toast.error(detail || t("setup.failed"));
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthSetup = async () => {
    setLoading(true);
    try {
      const res = await client.get("/system/setup/oauth/start");
      window.location.href = res.data.authorization_url;
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("setup.failed"));
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card glass-login">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div className="login-title">{t("app.title")}</div>
          <LanguageSwitcher />
        </div>
        <Text type="tertiary" style={{ display: "block", marginBottom: 16 }}>
          {t("setup.subtitle")}
        </Text>

        {isOAuth ? (
          <>
            <Text style={{ display: "block", marginBottom: 16 }}>
              {t("setup.oauthHint")}
            </Text>
            <Button
              theme="solid"
              block
              loading={loading}
              onClick={handleOAuthSetup}
            >
              {t("setup.oauthButton", {
                provider: status?.auth_type === "oauth" ? "OAuth" : "",
              })}
            </Button>
          </>
        ) : (
          <Form onSubmit={handleSubmit}>
            <Form.Input
              field="username"
              label={t("setup.username")}
              placeholder={t("setup.usernamePlaceholder")}
              rules={[{ required: true, message: t("setup.usernameRequired") }]}
            />
            <Form.Input
              field="password"
              label={t("setup.password")}
              mode="password"
              placeholder={t("setup.passwordPlaceholder")}
              rules={[{ required: true, message: t("setup.passwordRequired") }]}
            />
            <Form.Input
              field="confirmPassword"
              label={t("setup.confirmPassword")}
              mode="password"
              placeholder={t("setup.confirmPasswordPlaceholder")}
              rules={[
                { required: true, message: t("setup.confirmPasswordRequired") },
              ]}
            />
            <Form.Input
              field="display_name"
              label={t("setup.displayName")}
              placeholder={t("setup.displayNamePlaceholder")}
            />
            <Form.Input
              field="email"
              label={t("setup.email")}
              placeholder={t("setup.emailPlaceholder")}
            />
            <Button
              theme="solid"
              htmlType="submit"
              loading={loading}
              block
              style={{ marginTop: 16 }}
            >
              {t("setup.submit")}
            </Button>
          </Form>
        )}
      </Card>
    </div>
  );
}
