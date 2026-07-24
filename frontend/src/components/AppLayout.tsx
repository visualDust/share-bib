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
import "../styles/surfaces.css";

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

  useEffect(() => {
    const handleProfileUpdate = (event: Event) => {
      const profile = (event as CustomEvent<{ username?: string }>).detail;
      if (profile?.username) setUsername(profile.username);
    };
    window.addEventListener("sharebib-profile-updated", handleProfileUpdate);
    return () =>
      window.removeEventListener(
        "sharebib-profile-updated",
        handleProfileUpdate,
      );
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
      <header className="app-header">
        <div className="app-header-left">
          <button
            type="button"
            className="brand-lockup"
            onClick={() => navigate("/")}
            aria-label={status?.branding || t("app.title")}
          >
            <span className="brand-mark" aria-hidden="true">
              <IconTabs size="large" />
            </span>
            {!isMobile && status?.branding && (
              <span className="brand-name">{status.branding}</span>
            )}
          </button>
          <nav className="header-nav">
            {username && (
              <>
                <button
                  type="button"
                  className={`header-nav-item${location.pathname === "/" ? " active" : ""}`}
                  onClick={() => navigate("/")}
                  aria-current={location.pathname === "/" ? "page" : undefined}
                >
                  {t(isMobile ? "nav.collectionsShort" : "nav.collections")}
                </button>
                <button
                  type="button"
                  className={`header-nav-item${location.pathname === "/crawl-tasks" ? " active" : ""}`}
                  onClick={() => navigate("/crawl-tasks")}
                  aria-current={
                    location.pathname === "/crawl-tasks" ? "page" : undefined
                  }
                >
                  {t(isMobile ? "nav.crawlTasksShort" : "nav.crawlTasks")}
                </button>
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
                <Avatar size="small" color="grey">
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
      </header>

      <div className="app-content-wrapper">
        <div className="app-content-main">
          <div className="app-content-inner">{children}</div>
        </div>
      </div>
    </div>
  );
}
