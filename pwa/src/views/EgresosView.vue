<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../api/client";

const egresos = ref<any[]>([]);
const loading = ref(true);
const mostrar = ref(false);
const sesion = ref<any | null>(null);
const nuevo = ref({ id_sesion_caja: 0, categoria: "general", descripcion: "", monto: 0 });

async function cargar() {
  loading.value = true;
  try {
    const [egr, caja] = await Promise.all([
      api.get("/egresos/"),
      api.get("/caja/abierta"),
    ]);
    egresos.value = egr.data;
    sesion.value = caja.data;
  } finally {
    loading.value = false;
  }
}

async function guardar() {
  if (!nuevo.value.descripcion || nuevo.value.monto <= 0) return;
  try {
    await api.post("/egresos/", {
      id_sesion_caja: nuevo.value.id_sesion_caja,
      id_sucursal: sesion.value?.id_sucursal ?? 1,
      categoria: nuevo.value.categoria,
      descripcion: nuevo.value.descripcion,
      monto: nuevo.value.monto,
    });
    mostrar.value = false;
    nuevo.value = { id_sesion_caja: 0, categoria: "general", descripcion: "", monto: 0 };
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al registrar egreso");
  }
}

function abrirForm() {
  if (!sesion.value) {
    alert("Requiere una sesion de caja abierta");
    return;
  }
  nuevo.value.id_sesion_caja = sesion.value.id_sesion_caja;
  mostrar.value = true;
}

onMounted(cargar);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Egresos de Caja</h1>
      <div class="header-actions">
        <router-link to="/" class="btn-back">Volver</router-link>
        <button @click="abrirForm" class="primary">Registrar Egreso</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <div v-if="!sesion" class="empty">No hay sesion de caja abierta</div>
      <div v-if="egresos.length === 0 && sesion" class="empty">No hay egresos registrados</div>
      <div v-for="e in egresos" :key="e.id_egreso" class="egreso-row card">
        <div class="egreso-info">
          <span class="egreso-desc">{{ e.descripcion }}</span>
          <span class="muted">{{ new Date(e.fecha).toLocaleString() }} | {{ e.categoria }}</span>
        </div>
        <span class="monto">-${{ e.monto.toLocaleString() }}</span>
      </div>
    </div>

    <div v-if="mostrar" class="modal-overlay" @click.self="mostrar = false">
      <div class="modal">
        <h3>Registrar Egreso</h3>
        <label>Categoria</label>
        <select v-model="nuevo.categoria">
          <option>general</option>
          <option>renta</option>
          <option>servicios</option>
          <option>insumos</option>
          <option>retiro</option>
        </select>
        <label>Descripcion</label>
        <input v-model="nuevo.descripcion" placeholder="Ej: compra de agua, pago luz" />
        <label>Monto</label>
        <input v-model.number="nuevo.monto" type="number" min="1" />
        <div class="modal-actions">
          <button @click="guardar" class="primary" :disabled="!nuevo.descripcion || !nuevo.monto">Guardar</button>
          <button @click="mostrar = false" class="secondary">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-actions { display: flex; gap: 12px; align-items: center; }
.btn-back { color: var(--accent); text-decoration: none; }
.muted { color: var(--text-muted); font-size: 12px; }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 40px; }
.egreso-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; margin-bottom: 8px; }
.egreso-info { display: flex; flex-direction: column; }
.monto { font-weight: 700; color: var(--danger); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; width: 100%; max-width: 400px; }
.modal label { display: block; font-size: 12px; color: var(--text-muted); margin: 10px 0 4px; }
.modal select, .modal input { width: 100%; }
.modal-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>