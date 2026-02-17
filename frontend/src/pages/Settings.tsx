import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Card,
  Select,
  Button,
  Modal,
  Form,
  Toast,
  Input,
  Spin,
} from "@douyinfe/semi-ui-19";
import { IconArrowLeft, IconTick, IconClose } from "@douyinfe/semi-icons";
import client from "../api/client";
import "../styles/glass.css";

const { Title, Text } = Typography;

interface UserInfo {
  username: string;
  display_name: string | null;
  email: string | null;
}

export default function Settings() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  // Language & Theme
  const [language, setLanguage] = useState<string>("auto");
  const [theme, setTheme] = useState<string>("auto");

  // Password modal
  const [pwdVisible, setPwdVisible] = useState(false);
  const [pwdSubmitting, setPwdSubmitting] = useState(false);
  const pwdFormRef = useRef<any>(null);

  // Profile modal
  const [profileVisible, setProfileVisible] = useState(false);
  const [profileSubmitting, setProfileSubmitting] = useState(false);
  const [profileForm, setProfileForm] = useState({
    username: "",
    display_name: "",
    email: "",
  });
  const [profileErrors, setProfileErrors] = useState<Record<string, string>>(
    {},
  );
  const checkTimerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>(
    {},
  );

  useEffect(() => {
    // Load user info
    client
      .get("/auth/me")
      .then((res) => {
        setUserInfo(res.data);
        setProfileForm({
          username: res.data.username,
          display_name: res.data.display_name || "",
          email: res.data.email || "",
        });
      })
      .catch(() => navigate("/login"))
      .finally(() => setLoading(false));

    // Load language preference
    const savedLang = localStorage.getItem("i18nextLng");
    if (savedLang === "zh" || savedLang === "en") {
      setLanguage(savedLang);
    } else {
      setLanguage("auto");
    }

    // Load theme preference
    const savedTheme = localStorage.getItem("theme");
    setTheme(savedTheme || "auto");
  }, [navigate]);

  const handleLanguageChange = (value: string) => {
    setLanguage(value);
    if (value === "auto") {
      localStorage.removeItem("i18nextLng");
      const browserLang = navigator.language.toLowerCase().startsWith("zh")
        ? "zh"
        : "en";
      i18n.changeLanguage(browserLang);
    } else {
      i18n.changeLanguage(value);
    }
  };

  const handleThemeChange = (value: string) => {
    setTheme(value);
    if (value === "auto") {
      localStorage.removeItem("theme");
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      document.body.setAttribute("theme-mode", prefersDark ? "dark" : "light");
    } else {
      localStorage.setItem("theme", value);
      document.body.setAttribute("theme-mode", value);
    }
  };

  const handleChangePassword = async (values: {
    old_password: string;
    new_password: string;
    confirm_password: string;
  }) => {
    if (values.new_password !== values.confirm_password) {
      Toast.warning(t("settings.passwordMismatch"));
      return;
    }
    setPwdSubmitting(true);
    try {
      await client.put("/users/me/change-password", {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      Toast.success(t("settings.saveSuccess"));
      setPwdVisible(false);
      pwdFormRef.current?.formApi?.reset();
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("settings.saveFailed"));
    } finally {
      setPwdSubmitting(false);
    }
  };

  const checkField = (field: string, value: string) => {
    if (checkTimerRef.current[field])
      clearTimeout(checkTimerRef.current[field]);
    if (!value) {
      setProfileErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    if (field === "username" && value === userInfo?.username) {
      setProfileErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    if (field === "email" && value === (userInfo?.email || "")) {
      setProfileErrors((prev) => {
        const n = { ...prev };
        delete n[field];
        return n;
      });
      return;
    }
    checkTimerRef.current[field] = setTimeout(async () => {
      try {
        const res = await client.get("/users/me/check", {
          params: { field, value },
        });
        setProfileErrors((prev) => {
          const n = { ...prev };
          if (res.data.available) {
            delete n[field];
          } else {
            n[field] =
              field === "username"
                ? t("settings.usernameConflict")
                : t("settings.emailConflict");
          }
          return n;
        });
      } catch {
        /* ignore */
      }
    }, 300);
  };

  const handleProfileFieldChange = (field: string, value: string) => {
    setProfileForm((prev) => ({ ...prev, [field]: value }));
    if (field === "username" || field === "email") {
      checkField(field, value);
    }
  };

  const handleProfileSubmit = async () => {
    if (Object.keys(profileErrors).length > 0) {
      Toast.warning(t("admin.fixConflicts"));
      return;
    }
    if (!profileForm.username) {
      Toast.warning(t("settings.usernameRequired"));
      return;
    }
    setProfileSubmitting(true);
    try {
      await client.put("/users/me", {
        username: profileForm.username,
        display_name: profileForm.display_name || null,
        email: profileForm.email || null,
      });
      Toast.success(t("settings.saveSuccess"));
      setUserInfo({
        username: profileForm.username,
        display_name: profileForm.display_name || null,
        email: profileForm.email || null,
      });
      setProfileVisible(false);
    } catch (err: any) {
      Toast.error(err.response?.data?.detail || t("settings.saveFailed"));
    } finally {
      setProfileSubmitting(false);
    }
  };

  if (loading)
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );

  return (
    <div>
      <Button
        icon={<IconArrowLeft />}
        theme="borderless"
        onClick={() => navigate("/")}
        style={{ marginBottom: 16 }}
      >
        {t("collection.back")}
      </Button>

      <Title heading={3} style={{ marginBottom: 24 }}>
        {t("settings.title")}
      </Title>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 16,
          maxWidth: 600,
        }}
      >
        <Card className="glass-card">
          <div style={{ marginBottom: 16 }}>
            <label className="form-label">{t("settings.language")}</label>
            <Select
              value={language}
              onChange={(v) => handleLanguageChange(v as string)}
              style={{ width: "100%" }}
            >
              <Select.Option value="auto">
                {t("settings.languageAuto")}
              </Select.Option>
              <Select.Option value="zh">
                {t("settings.languageChinese")}
              </Select.Option>
              <Select.Option value="en">
                {t("settings.languageEnglish")}
              </Select.Option>
            </Select>
          </div>
          <div>
            <label className="form-label">{t("settings.theme")}</label>
            <Select
              value={theme}
              onChange={(v) => handleThemeChange(v as string)}
              style={{ width: "100%" }}
            >
              <Select.Option value="auto">
                {t("settings.themeAuto")}
              </Select.Option>
              <Select.Option value="light">
                {t("settings.themeLight")}
              </Select.Option>
              <Select.Option value="dark">
                {t("settings.themeDark")}
              </Select.Option>
            </Select>
          </div>
        </Card>

        <Card className="glass-card">
          <Title heading={5} style={{ marginBottom: 16 }}>
            {t("settings.account")}
          </Title>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <Text strong>{t("settings.username")}</Text>
                <div>
                  <Text type="tertiary">{userInfo?.username}</Text>
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <Text strong>{t("settings.displayName")}</Text>
                <div>
                  <Text type="tertiary">{userInfo?.display_name || "-"}</Text>
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <Text strong>{t("settings.email")}</Text>
                <div>
                  <Text type="tertiary">{userInfo?.email || "-"}</Text>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <Button theme="solid" onClick={() => setProfileVisible(true)}>
                {t("settings.editProfile")}
              </Button>
              <Button onClick={() => setPwdVisible(true)}>
                {t("settings.changePassword")}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Change Password Modal */}
      <Modal
        title={t("settings.changePassword")}
        visible={pwdVisible}
        onCancel={() => {
          setPwdVisible(false);
          pwdFormRef.current?.formApi?.reset();
        }}
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button
              onClick={() => {
                setPwdVisible(false);
                pwdFormRef.current?.formApi?.reset();
              }}
            >
              {t("settings.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={pwdSubmitting}
              onClick={() => pwdFormRef.current?.formApi?.submitForm()}
            >
              {t("settings.save")}
            </Button>
          </div>
        }
      >
        <Form ref={pwdFormRef} onSubmit={handleChangePassword}>
          <Form.Input
            field="old_password"
            label={t("settings.currentPassword")}
            mode="password"
            rules={[
              {
                required: true,
                message: t("settings.currentPasswordRequired"),
              },
            ]}
          />
          <Form.Input
            field="new_password"
            label={t("settings.newPassword")}
            mode="password"
            rules={[
              { required: true, message: t("settings.newPasswordRequired") },
            ]}
          />
          <Form.Input
            field="confirm_password"
            label={t("settings.confirmPassword")}
            mode="password"
            rules={[
              {
                required: true,
                message: t("settings.confirmPasswordRequired"),
              },
            ]}
          />
        </Form>
      </Modal>

      {/* Edit Profile Modal */}
      <Modal
        title={t("settings.editProfile")}
        visible={profileVisible}
        onCancel={() => {
          setProfileVisible(false);
          setProfileErrors({});
        }}
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button
              onClick={() => {
                setProfileVisible(false);
                setProfileErrors({});
              }}
            >
              {t("settings.cancel")}
            </Button>
            <Button
              theme="solid"
              loading={profileSubmitting}
              onClick={handleProfileSubmit}
            >
              {t("settings.save")}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label className="form-label">{t("settings.username")}</label>
            <Input
              value={profileForm.username}
              onChange={(v) => handleProfileFieldChange("username", v)}
              suffix={
                profileErrors.username ? (
                  <IconClose style={{ color: "var(--semi-color-danger)" }} />
                ) : profileForm.username &&
                  profileForm.username !== userInfo?.username ? (
                  <IconTick style={{ color: "var(--semi-color-success)" }} />
                ) : null
              }
            />
            {profileErrors.username && (
              <div
                style={{
                  color: "var(--semi-color-danger)",
                  fontSize: 12,
                  marginTop: 2,
                }}
              >
                {profileErrors.username}
              </div>
            )}
          </div>
          <div>
            <label className="form-label">{t("settings.displayName")}</label>
            <Input
              value={profileForm.display_name}
              onChange={(v) => handleProfileFieldChange("display_name", v)}
            />
          </div>
          <div>
            <label className="form-label">{t("settings.email")}</label>
            <Input
              value={profileForm.email}
              onChange={(v) => handleProfileFieldChange("email", v)}
              suffix={
                profileErrors.email ? (
                  <IconClose style={{ color: "var(--semi-color-danger)" }} />
                ) : profileForm.email &&
                  profileForm.email !== (userInfo?.email || "") ? (
                  <IconTick style={{ color: "var(--semi-color-success)" }} />
                ) : null
              }
            />
            {profileErrors.email && (
              <div
                style={{
                  color: "var(--semi-color-danger)",
                  fontSize: 12,
                  marginTop: 2,
                }}
              >
                {profileErrors.email}
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}
