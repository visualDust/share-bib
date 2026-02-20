import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Dropdown, Typography, Avatar } from "@douyinfe/semi-ui-19";
import {
  IconUpload,
  IconExit,
  IconUser,
  IconSetting,
} from "@douyinfe/semi-icons";
import { IconTabs } from "@douyinfe/semi-icons-lab";
import client from "../api/client";
import { useSystemStatus } from "../App";
import "../styles/glass.css";

const { Text } = Typography;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const { status } = useSystemStatus();
  const [username, setUsername] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [collectionTitle, setCollectionTitle] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    client
      .get("/auth/me")
      .then((res) => {
        setUsername(res.data.username);
        setIsAdmin(res.data.is_admin || false);
      })
      .catch(() => {});
  }, []);

  // Fetch collection title when on collection detail page
  useEffect(() => {
    const match = location.pathname.match(/^\/collections\/([^/]+)$/);
    if (match) {
      const collectionId = match[1];
      client
        .get(`/collections/${collectionId}`)
        .then((res) => setCollectionTitle(res.data.title))
        .catch(() => setCollectionTitle(null));
    } else {
      setCollectionTitle(null);
    }
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <div className="app-layout">
      <div
        className="app-header glass-header main-header"
        style={{
          backgroundColor:
            "color-mix(in srgb, var(--semi-color-bg-0) 85%, transparent)",
          backdropFilter: "blur(16px) saturate(180%)",
          WebkitBackdropFilter: "blur(16px) saturate(180%)",
          borderBottom: "1px solid var(--semi-color-border)",
        }}
      >
        <div className="app-header-left">
          <IconTabs
            size="extra-large"
            className="logo-icon"
            onClick={() => navigate("/")}
            style={{ cursor: "pointer" }}
          />
          {!isMobile && status?.branding && (
            <Text
              strong
              style={{
                fontSize: "18px",
                marginLeft: "8px",
                color: "var(--semi-color-text-0)",
              }}
            >
              {status.branding}
            </Text>
          )}
          <nav className="header-nav">
            {username && (
              <>
                <span
                  className={`header-nav-item${location.pathname === "/" ? " active" : ""}`}
                  onClick={() => navigate("/")}
                >
                  {t(isMobile ? "nav.collectionsShort" : "nav.collections")}
                </span>
                <span
                  className={`header-nav-item${location.pathname === "/crawl-tasks" ? " active" : ""}`}
                  onClick={() => navigate("/crawl-tasks")}
                >
                  {t(isMobile ? "nav.crawlTasksShort" : "nav.crawlTasks")}
                </span>
              </>
            )}
          </nav>
          {collectionTitle && (
            <Text strong className="header-collection-title">
              {collectionTitle}
            </Text>
          )}
        </div>
        <div className="app-header-right">
          {username ? (
            <Dropdown
              trigger="click"
              clickToHide
              position="bottomRight"
              render={
                <Dropdown.Menu>
                  <Dropdown.Item
                    icon={<IconUser />}
                    onClick={() => navigate(`/user/${username}`)}
                  >
                    {t("nav.profile")}
                  </Dropdown.Item>
                  <Dropdown.Item
                    icon={<IconUpload />}
                    onClick={() => navigate("/import")}
                  >
                    {t("nav.import")}
                  </Dropdown.Item>
                  {isAdmin && (
                    <Dropdown.Item
                      icon={<IconSetting />}
                      onClick={() => navigate("/admin")}
                    >
                      {t("nav.admin")}
                    </Dropdown.Item>
                  )}
                  <Dropdown.Item
                    icon={<IconSetting />}
                    onClick={() => navigate("/settings")}
                  >
                    {t("nav.settings")}
                  </Dropdown.Item>
                  <Dropdown.Divider />
                  <Dropdown.Item
                    icon={<IconExit />}
                    type="danger"
                    onClick={handleLogout}
                  >
                    {t("nav.logout")}
                  </Dropdown.Item>
                </Dropdown.Menu>
              }
            >
              <div className="user-menu-trigger">
                <Avatar size="small" color="blue">
                  {username.charAt(0).toUpperCase()}
                </Avatar>
                {!isMobile && (
                  <span className="user-menu-name">{username}</span>
                )}
              </div>
            </Dropdown>
          ) : (
            <Button onClick={() => navigate("/login")}>{t("nav.login")}</Button>
          )}
        </div>
      </div>

      <div className="app-content-wrapper">
        <div className="content-gradient-overlay">
          <div className="content-blur-layer" />
          <div className="content-color-layer" />
        </div>
        <div className="app-content-main">
          <div className="app-content-inner">{children}</div>
        </div>
      </div>
    </div>
  );
}
