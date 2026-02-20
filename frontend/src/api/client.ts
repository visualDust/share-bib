import axios from "axios";
import i18n from "../i18n";

const client = axios.create({
  baseURL: "/api",
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers["Accept-Language"] = i18n.language || "en";
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Don't redirect for system/setup endpoints (unauthenticated by design)
      // or for public collection views, or for /auth/me (used to check login status)
      const url = err.config?.url || "";
      const isSystemEndpoint = url.includes("/system/");
      const isAuthMe = url === "/auth/me";
      const isCollectionView = url.match(/^\/collections\/[^/]+$/);
      const isCollectionExport = url.match(/^\/collections\/[^/]+\/export\//);

      if (
        !isSystemEndpoint &&
        !isAuthMe &&
        !isCollectionView &&
        !isCollectionExport
      ) {
        localStorage.removeItem("token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  },
);

export default client;
