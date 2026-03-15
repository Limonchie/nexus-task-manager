import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api, type User } from "../api/client";

type AuthState = {
  user: User | null;
  setUser: (u: User | null) => void;
  logout: () => Promise<void>;
  fetchMe: () => Promise<User | null>;
  isAuthenticated: boolean;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: async () => {
        await api.post("/auth/logout").catch(() => {});
        set({ user: null, isAuthenticated: false });
      },
      fetchMe: async () => {
        try {
          const user = await api.get<User>("/auth/me");
          set({ user, isAuthenticated: true });
          return user;
        } catch {
          set({ user: null, isAuthenticated: false });
          return null;
        }
      },
    }),
    { name: "nexus-auth" }
  )
);
