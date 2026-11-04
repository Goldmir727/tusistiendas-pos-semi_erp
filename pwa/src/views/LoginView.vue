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

async function handleLogin() {
  loading.value = true;
  error.value = "";
  try {
    await authStore.login(email.value, contrasena.value);
    router.push("/");
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || "Error de autenticacion";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card card">
      <h1>POS System</h1>
      <p class="subtitle">Inicia sesion para continuar</p>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="correo@ejemplo.com" required />
        </div>
        <div class="field">
          <label>Contrasena</label>
          <input v-model="contrasena" type="password" placeholder="Contrasena" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="primary full-width" :disabled="loading">
          {{ loading ? "Ingresando..." : "Ingresar" }}
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
</style>
