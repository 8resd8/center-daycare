import api from "./client";

export interface UserInfo {
  user_id: number;
  username: string;
  name: string;
  role: string;
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<UserInfo>("/auth/login", { username, password }),

  me: () => api.get<UserInfo>("/auth/me"),

  logout: () => api.post("/auth/logout"),
};
