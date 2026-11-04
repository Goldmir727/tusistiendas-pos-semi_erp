<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../stores/auth";
import api from "../api/client";

const authStore = useAuthStore();
const stats = ref({
  ventasHoy: 0,
  productosBajoStock: 0,
  turnosActivos: 0,
});

onMounted(async () => {
  try {
    const [ventas, stock] = await Promise.all([
      api.get("/reportes/ventas-por-dia", { params: { fecha_desde: new Date().toISOString().split("T")[0], fecha_hasta: new Date().toISOString().split("T")[0] } }),
      api.get("/reportes/stock-critico"),
    ]);
    stats.value.ventasHoy = ventas.data.reduce((sum: number, v: any) => sum + v.total, 0);
    stats.value.productosBajoStock = stock.data.length;
  } catch {}
});
</script>

<template>
  <div class="dashboard">
    <header class="top-bar">
      <h1>POS System</h1>
      <div class="user-info">
        <span>{{ authStore.user?.nombre_completo }}</span>
        <button @click="authStore.logout()" class="btn-sm">Salir</button>
      </div>
    </header>
    <main class="content">
      <div class="stats-grid">
        <div class="stat-card card">
          <span class="stat-label">Ventas Hoy</span>
          <span class="stat-value">${{ stats.ventasHoy.toLocaleString() }}</span>
        </div>
        <div class="stat-card card">
          <span class="stat-label">Stock Critico</span>
          <span class="stat-value warning">{{ stats.productosBajoStock }}</span>
        </div>
      </div>
      <nav class="quick-nav">
        <router-link to="/pos" class="nav-btn card">Abrir POS</router-link>
        <router-link to="/turnos" class="nav-btn card">Mis Turnos</router-link>
        <router-link to="/pagos" class="nav-btn card">Mis Pagos</router-link>
        <router-link to="/clientes" class="nav-btn card">Clientes y Fiado</router-link>
        <router-link to="/compras" class="nav-btn card">Compras e Inventario</router-link>
        <router-link to="/devoluciones" class="nav-btn card">Devoluciones</router-link>
        <router-link to="/egresos" class="nav-btn card">Egresos</router-link>
        <router-link v-if="authStore.user?.rol === 'administrador'" to="/admin" class="nav-btn card">Admin</router-link>
      </nav>
    </main>
  </div>
</template>

<style scoped>
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--primary);
  border-bottom: 1px solid var(--border);
}
.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
  background: var(--border);
  color: var(--text);
}
.content {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}
.stat-card {
  text-align: center;
}
.stat-label {
  display: block;
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
}
.stat-value.warning {
  color: var(--warning);
}
.quick-nav {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
  padding: 32px;
  transition: transform 0.2s, border-color 0.2s;
}
.nav-btn:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
}
</style>
