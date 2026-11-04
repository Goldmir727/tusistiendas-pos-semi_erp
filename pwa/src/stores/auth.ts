import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../api/client";

interface User {
  id_usuario: number;
  nombre_completo: string;
  email: string;
  documento_identidad: string;
  rol: string;
  id_sucursal: number | null;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const user = ref<User | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  async function login(email: string, contrasena: string) {
    const response = await api.post("/auth/login", {
      email: email,
      contrasena: contrasena,
    });

    const access = response.data.access_token as string;
    const refresh = response.data.refresh_token as string;
    token.value = access;
    refreshToken.value = refresh;
    localStorage.setItem("token", access);
    localStorage.setItem("refreshToken", refresh);

    await fetchUser();
  }

  async function fetchUser() {
    try {
      const response = await api.get("/usuarios/me");
      user.value = response.data;
    } catch {
      logout();
    }
  }

  function logout() {
    token.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
  }

  return { token, refreshToken, user, isAuthenticated, login, fetchUser, logout };
});
