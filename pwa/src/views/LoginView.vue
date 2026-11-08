<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const email = ref("");
const contrasena = ref("");
const error = ref("");
const loading = ref(false);
const paso = ref<"credenciales" | "codigo">("credenciales");
const challengeId = ref("");
const emailMasked = ref("");
const codigo = ref("");
const recordar = ref(true);
const devCode = ref("");

async function handleLogin() {
  loading.value = true;
  error.value = "";
  try {
    const res = await authStore.login(email.value, contrasena.value, recordar.value);
    if (res.requires2fa) {
      challengeId.value = res.challengeId ?? "";
      emailMasked.value = res.emailMasked ?? "";
      devCode.value = res.devCode || "";
      paso.value = "codigo";
    } else {
      router.push("/");
    }
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || "Error de autenticacion";
  } finally {
    loading.value = false;
  }
}

async function handleVerify() {
  loading.value = true;
  error.value = "";
  try {
    await authStore.verify2fa(challengeId.value, codigo.value, recordar.value, "Dispositivo POS");
    router.push("/");
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || "Codigo invalido";
  } finally {
    loading.value = false;
  }
}

async function handleResend() {
  try {
    const data = await authStore.resendCode(challengeId.value);
    devCode.value = data.dev_code || devCode.value;
    error.value = "Codigo reenviado";
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || "No se pudo reenviar";
  }
}

function volver() {
  paso.value = "credenciales";
  codigo.value = "";
  error.value = "";
}
</script>

<template>
  <div class="login-container">
    <div class="login-card card">
      <h1>POS System</h1>
      <p class="subtitle">Inicia sesion para continuar</p>

      <form v-if="paso === 'credenciales'" @submit.prevent="handleLogin">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="correo@ejemplo.com" required />
        </div>
        <div class="field">
          <label>Contrasena</label>
          <input v-model="contrasena" type="password" placeholder="Contrasena" required />
        </div>
        <div class="field" style="display: flex; align-items: center; gap: 8px;">
          <input id="recordar" v-model="recordar" type="checkbox" />
          <label for="recordar" style="margin: 0;">Recordar este dispositivo</label>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="primary full-width" :disabled="loading">
          {{ loading ? "Ingresando..." : "Ingresar" }}
        </button>
      </form>

      <form v-else @submit.prevent="handleVerify">
        <p class="subtitle">Codigo enviado a {{ emailMasked }}</p>
        <div v-if="devCode" class="error" style="background: #fff3cd; color: #856404; padding: 8px; border-radius: 4px;">
          Codigo de desarrollo: {{ devCode }}
        </div>
        <div class="field">
          <label>Codigo de 6 digitos</label>
          <input v-model="codigo" type="text" inputmode="numeric" maxlength="6" required />
        </div>
        <div class="field" style="display: flex; align-items: center; gap: 8px;">
          <input id="recordar2" v-model="recordar" type="checkbox" />
          <label for="recordar2" style="margin: 0;">Recordar este dispositivo</label>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="primary full-width" :disabled="loading">
          {{ loading ? "Verificando..." : "Verificar" }}
        </button>
        <button type="button" class="secundario full-width" style="margin-top: 8px;" @click="handleResend">
          Reenviar codigo
        </button>
        <button type="button" class="enlace" style="margin-top: 8px;" @click="volver">
          Volver
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
}
.login-card {
  width: 100%;
  max-width: 400px;
  text-align: center;
}
h1 {
  font-size: 28px;
  margin-bottom: 8px;
  color: var(--accent);
}
.subtitle {
  color: var(--text-muted);
  margin-bottom: 24px;
}
.field {
  margin-bottom: 16px;
  text-align: left;
}
label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-muted);
}
.full-width {
  width: 100%;
  padding: 12px;
}
.error {
  color: var(--danger);
  font-size: 13px;
  margin-bottom: 12px;
}
.secundario {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}
.enlace {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
}
</style>