import axios from "axios";
import { useAuthStore } from "@/store/authStore";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  withCredentials: true,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ?? err.message ?? "알 수 없는 오류";
    console.error("[API Error]", message);

    if (
      err.response?.status === 401 &&
      !window.location.pathname.includes("/login")
    ) {
      useAuthStore.getState().clearAuth();
      window.location.href = "/login";
    }

    return Promise.reject(err);
  }
);

export default api;
