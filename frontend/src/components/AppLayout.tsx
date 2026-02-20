import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Dropdown, Typography } from "@douyinfe/semi-ui-19";
import {
  IconUpload,
  IconExit,
  IconUser,
  IconSetting,
} from "@douyinfe/semi-icons";
import { IconTabs } from "@douyinfe/semi-icons-lab";
import client from "../api/client";
import "../styles/glass.css";

const { Text } = Typography;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const [username, setUsername] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [collectionTitle, setCollectionTitle] = useState<string | null>(null);

  const [isDarkMode, setIsDarkMode] = useState(
    document.body.getAttribute("theme-mode") === "dark",
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDarkMode(document.body.getAttribute("theme-mode") === "dark");
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["theme-mode"],
    });
    return () => observer.disconnect();
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

  const particleColor = isDarkMode
    ? "rgba(255, 255, 255, 0.15)"
    : "rgba(0, 0, 0, 0.15)";

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
        <div className="header-overlay" />
        <div className="header-particles">
          {[...Array(12)].map((_, i) => (
            <div
              key={i}
              className="header-particle"
              style={{
                background: particleColor,
                boxShadow: `0 0 8px ${particleColor}`,
              }}
            />
          ))}
        </div>
        <div className="header-shooting-stars">
          <div
            className="header-shooting-star"
            style={{
              background: particleColor,
              boxShadow: `0 0 8px 2px ${particleColor}`,
            }}
          />
        </div>

        <div className="app-header-left">
          <IconTabs
            size="extra-large"
            className="logo-icon"
            onClick={() => navigate("/")}
            style={{ cursor: "pointer" }}
          />
          <nav className="header-nav">
            <span
              className={`header-nav-item${location.pathname === "/" ? " active" : ""}`}
              onClick={() => navigate("/")}
            >
              {t("nav.collections")}
            </span>
            <span
              className={`header-nav-item${location.pathname === "/crawl-tasks" ? " active" : ""}`}
              onClick={() => navigate("/crawl-tasks")}
            >
              {t("nav.crawlTasks")}
            </span>
          </nav>
          {collectionTitle && (
            <Text strong className="header-collection-title">
              {collectionTitle}
            </Text>
          )}
        </div>
        <div className="app-header-right">
          <Dropdown
            trigger="click"
            clickToHide
            position="bottomRight"
            render={
              <Dropdown.Menu>
                {username && (
                  <Dropdown.Item
                    icon={<IconUser />}
                    onClick={() => navigate(`/user/${username}`)}
                  >
                    {t("nav.profile")}
                  </Dropdown.Item>
                )}
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
            <span style={{ display: "inline-flex" }}>
              <Button icon={<IconUser />} theme="borderless">
                {username || ""}
              </Button>
            </span>
          </Dropdown>
        </div>
      </div>

      <div className="app-content-wrapper">
        <div className="content-gradient-overlay">
          <div className="content-blur-layer" />
          <div className="content-color-layer" />
          <div className="content-particles">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="content-particle"
                style={{
                  background: particleColor,
                  boxShadow: `0 0 10px 2px ${particleColor}`,
                }}
              />
            ))}
            <div
              className="content-shooting-star"
              style={{
                background: particleColor,
                boxShadow: `0 0 12px 3px ${particleColor}`,
              }}
            />
          </div>
        </div>
        <div className="app-content-main">
          <div className="app-content-inner">{children}</div>
        </div>
      </div>
    </div>
  );
}
