import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, Form, Button, Toast } from "@douyinfe/semi-ui-19";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useSystemStatus } from "../App";
import client from "../api/client";
import "../styles/glass.css";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { status } = useSystemStatus();

  const isOAuth = status?.auth_type === "oauth" && status?.oauth_configured;

  const handleSubmit = async (values: {
    username: string;
    password: string;
  }) => {
    setLoading(true);
    try {
      const res = await client.post("/auth/login", values);
      localStorage.setItem("token", res.data.access_token);
      navigate("/");
    } catch {
      Toast.error(t("login.failed"));
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = async () => {
    setLoading(true);
    try {
      const res = await client.get("/auth/oauth/start");
      window.location.href = res.data.authorization_url;
    } catch {
      Toast.error(t("login.oauthFailed"));
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

        {isOAuth ? (
          <Button
            theme="solid"
            block
            loading={loading}
            onClick={handleOAuthLogin}
            style={{ marginTop: 16 }}
          >
            {t("login.oauthButton")}
          </Button>
        ) : (
          <Form onSubmit={handleSubmit}>
            <Form.Input
              field="username"
              label={t("login.username")}
              placeholder={t("login.usernamePlaceholder")}
              rules={[{ required: true, message: t("login.usernameRequired") }]}
            />
            <Form.Input
              field="password"
              label={t("login.password")}
              mode="password"
              placeholder={t("login.passwordPlaceholder")}
              rules={[{ required: true, message: t("login.passwordRequired") }]}
            />
            <Button
              theme="solid"
              htmlType="submit"
              loading={loading}
              block
              style={{ marginTop: 16 }}
            >
              {t("login.submit")}
            </Button>
          </Form>
        )}
      </Card>
    </div>
  );
}
