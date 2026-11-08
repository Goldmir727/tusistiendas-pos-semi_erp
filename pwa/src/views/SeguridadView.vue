<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import api from "../api/client";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const dispositivos = ref<any[]>([]);
const loading = ref(true);
const dosFA = ref(false);
const toggling = ref(false);

const recordatorio = computed(() => !dosFA.value);

async function cargar() {
  try {
    dispositivos.value = await authStore.listDevices();
    const me = await api.get("/usuarios/me");
    dosFA.value = !!me.data?.auth_2fa_habilitado;
  } catch {}
  loading.value = false;
}

async function toggle2FA() {
  toggling.value = true;
  try {
    const resp = await api.patch("/auth/2fa", { habilitado: !dosFA.value });
    dosFA.value = !!resp.data?.habilitado;
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error");
  } finally {
    toggling.value = false;
  }
}

async function revocar(id: number) {
  try {
    await authStore.revokeDevice(id);
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error");
  }
}

onMounted(cargar);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Seguridad</h1>
      <router-link to="/" class="btn-back">Volver</router-link>
    </header>
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <div v-if="recordatorio" class="card" style="margin-bottom: 16px; border-color: var(--danger);">
        <h3>Activa la verificacion en dos pasos</h3>
        <p class="muted" style="text-align: left; padding: 8px 0;">
          Tu cuenta aun no tiene 2FA. Activalo para proteger el acceso desde dispositivos nuevos.
        </p>
        <button class="primary" :disabled="toggling" @click="toggle2FA">
          {{ toggling ? "Activando..." : "Activar 2FA" }}
        </button>
      </div>
      <div class="card" style="margin-bottom: 16px;">
        <h3>Verificacion en dos pasos (2FA)</h3>
        <p class="muted" style="text-align: left; padding: 8px 0;">
          Estado: <strong>{{ dosFA ? "Activado" : "Desactivado" }}</strong>
        </p>
        <button class="primary" :disabled="toggling" @click="toggle2FA">
          {{ toggling ? "Procesando..." : (dosFA ? "Desactivar 2FA" : "Activar 2FA") }}
        </button>
      </div>
      <div class="card">
        <h3>Dispositivos de confianza</h3>
        <div v-if="dispositivos.length === 0" class="muted">No hay dispositivos registrados</div>
        <div v-for="d in dispositivos" :key="d.id_dispositivo" class="turno-row">
          <div class="turno-info">
            <span>{{ d.nombre || "Dispositivo" }}</span>
            <span class="muted">{{ d.ip || "" }} - expira {{ new Date(d.expira_en).toLocaleDateString() }}</span>
          </div>
          <button class="mini peligro" @click="revocar(d.id_dispositivo)">Revocar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.btn-back { color: var(--accent); text-decoration: none; }
.loading, .muted { text-align: center; color: var(--text-muted); padding: 20px; }
.turno-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.turno-info { display: flex; flex-direction: column; flex: 1; }
.mini { padding: 4px 8px; font-size: 12px; }
.peligro { background: var(--danger); color: #fff; border: none; }
</style>