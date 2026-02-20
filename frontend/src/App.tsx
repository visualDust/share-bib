import { useState, useEffect, createContext, useContext } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "@douyinfe/semi-ui-19";
import Login from "./pages/Login";
import Setup from "./pages/Setup";
import Home from "./pages/Home";
import CollectionDetail from "./pages/CollectionDetail";
import Import from "./pages/Import";
import CrawlTasks from "./pages/CrawlTasks";
import UserProfile from "./pages/UserProfile";
import Admin from "./pages/Admin";
import Settings from "./pages/Settings";
import AppLayout from "./components/AppLayout";
import client from "./api/client";

interface SystemStatus {
  initialized: boolean;
  auth_type: string;
  oauth_configured: boolean;
  branding: string;
}

interface SystemContextValue {
  status: SystemStatus | null;
  setStatus: React.Dispatch<React.SetStateAction<SystemStatus | null>>;
}

const SystemContext = createContext<SystemContextValue>({
  status: null,
  setStatus: () => {},
});
export const useSystemStatus = () => useContext(SystemContext);

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Handle OAuth callback token in URL
    const params = new URLSearchParams(window.location.search);
    const tokenFromUrl = params.get("token");
    if (tokenFromUrl) {
      localStorage.setItem("token", tokenFromUrl);
      // Clean up URL
      window.history.replaceState({}, "", window.location.pathname);
    }

    client
      .get("/system/status")
      .then((res) => setStatus(res.data))
      .catch(() =>
        setStatus({
          initialized: true,
          auth_type: "simple",
          oauth_configured: false,
          branding: "",
        }),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return (
    <SystemContext.Provider value={{ status, setStatus }}>
      <Routes>
        <Route
          path="/setup"
          element={
            status?.initialized ? <Navigate to="/" replace /> : <Setup />
          }
        />
        <Route
          path="/login"
          element={
            !status?.initialized ? <Navigate to="/setup" replace /> : <Login />
          }
        />
        {/* Public collection view - accessible without login */}
        <Route
          path="/collections/:id"
          element={
            !status?.initialized ? (
              <Navigate to="/setup" replace />
            ) : (
              <AppLayout>
                <CollectionDetail />
              </AppLayout>
            )
          }
        />
        <Route
          path="/*"
          element={
            !status?.initialized ? (
              <Navigate to="/setup" replace />
            ) : (
              <PrivateRoute>
                <AppLayout>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/import" element={<Import />} />
                    <Route path="/crawl-tasks" element={<CrawlTasks />} />
                    <Route path="/user/:username" element={<UserProfile />} />
                    <Route path="/admin" element={<Admin />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </AppLayout>
              </PrivateRoute>
            )
          }
        />
      </Routes>
    </SystemContext.Provider>
  );
}
