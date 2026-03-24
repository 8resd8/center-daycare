import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ?? err.message ?? "알 수 없는 오류";
    console.error("[API Error]", message);
    return Promise.reject(err);
  }
);

export default api;
