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
  auth_2fa_habilitado?: boolean;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const deviceToken = ref<string | null>(localStorage.getItem("deviceToken"));
  const user = ref<User | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  function setTokens(access: string, refresh: string) {
    token.value = access;
    refreshToken.value = refresh;
    localStorage.setItem("token", access);
    localStorage.setItem("refreshToken", refresh);
  }

  async function login(email: string, contrasena: string, recordar: boolean) {
    const response = await api.post("/auth/login", {
      email,
      contrasena,
      device_token: deviceToken.value,
      recordar_dispositivo: recordar,
    });

    if (response.status === 202 || response.data?.requires_2fa) {
      return {
        requires2fa: true,
        challengeId: response.data.challenge_id as string,
        emailMasked: response.data.email_masked as string,
        devCode: response.data.dev_code as string | undefined,
        expiresIn: response.data.expires_in as number,
      };
    }

    const access = response.data.access_token as string;
    const refresh = response.data.refresh_token as string;
    setTokens(access, refresh);
    if (response.data.device_token) {
      deviceToken.value = response.data.device_token;
      localStorage.setItem("deviceToken", response.data.device_token);
    }
    await fetchUser();
    return { requires2fa: false };
  }

  async function verify2fa(
    challengeId: string,
    codigo: string,
    recordar: boolean,
    nombreDispositivo?: string
  ) {
    const response = await api.post("/auth/verificar-2fa", {
      challenge_id: challengeId,
      codigo,
      recordar_dispositivo: recordar,
      nombre_dispositivo: nombreDispositivo,
    });
    const access = response.data.access_token as string;
    const refresh = response.data.refresh_token as string;
    setTokens(access, refresh);
    if (response.data.device_token) {
      deviceToken.value = response.data.device_token;
      localStorage.setItem("deviceToken", response.data.device_token);
    }
    await fetchUser();
  }

  async function resendCode(challengeId: string) {
    const response = await api.post("/auth/reenviar-codigo", {
      challenge_id: challengeId,
    });
    return response.data;
  }

  async function fetchUser() {
    try {
      const response = await api.get("/usuarios/me");
      user.value = response.data;
    } catch {
      logout();
    }
  }

  async function revokeDevice(idDispositivo: number) {
    await api.delete(`/auth/dispositivos/${idDispositivo}`);
    if (idDispositivo && deviceToken.value) {
      // si se revoca el actual, limpiar token local
    }
  }

  async function listDevices() {
    const response = await api.get("/auth/dispositivos");
    return response.data || [];
  }

  function logout(redirigir = true) {
    token.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    if (redirigir && typeof window !== "undefined") {
      // Salir debe llevar de inmediato al login; si no, la vista actual queda
      // visible sin sesión y el siguiente clic termina redirigiendo por 401.
      window.location.replace("/login");
    }
  }

  function revokeLocalDevice() {
    deviceToken.value = null;
    localStorage.removeItem("deviceToken");
  }

  return {
    token,
    refreshToken,
    deviceToken,
    user,
    isAuthenticated,
    login,
    verify2fa,
    resendCode,
    fetchUser,
    revokeDevice,
    listDevices,
    logout,
    revokeLocalDevice,
  };
});