import axios, { AxiosRequestConfig } from "axios";
import { useAuthStore } from "@/store/authStore";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  withCredentials: true,
});

let _isRefreshing = false;
let _refreshQueue: Array<{ resolve: () => void; reject: (e: unknown) => void }> = [];

function _drainQueue(success: boolean, err?: unknown) {
  _refreshQueue.forEach((p) => (success ? p.resolve() : p.reject(err)));
  _refreshQueue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const config = err.config as AxiosRequestConfig & { _retry?: boolean };
    const status = err.response?.status;
    const isAuthEndpoint = config.url?.includes("/auth/");

    // auth 엔드포인트 자체의 401은 그냥 전파 (무한루프 방지)
    if (status !== 401 || isAuthEndpoint || config._retry) {
      const message = err.response?.data?.detail ?? err.message ?? "알 수 없는 오류";
      console.error("[API Error]", message);
      return Promise.reject(err);
    }

    // 이미 refresh 중이면 대기열에 추가
    if (_isRefreshing) {
      return new Promise((resolve, reject) => {
        _refreshQueue.push({
          resolve: () => resolve(api(config)),
          reject,
        });
      });
    }

    config._retry = true;
    _isRefreshing = true;

    try {
      // refresh_token 쿠키로 새 access_token 발급
      const { data } = await api.post<{ user_id: number; username: string; name: string; role: string }>(
        "/auth/refresh"
      );
      useAuthStore.getState().setUser(data);
      _drainQueue(true);
      return api(config);
    } catch (refreshErr) {
      _drainQueue(false, refreshErr);
      useAuthStore.getState().clearAuth();
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
      return Promise.reject(refreshErr);
    } finally {
      _isRefreshing = false;
    }
  }
);

export default api;
