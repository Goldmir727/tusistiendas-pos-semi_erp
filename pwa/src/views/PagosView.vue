<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import api from "../api/client";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const turnosPendientes = ref<any[]>([]);
const misPagos = ref<any[]>([]);
const empleados = ref<any[]>([]);
const empleadoSel = ref<number | null>(null);
const selected = ref<Set<number>>(new Set());
const loading = ref(true);

const esAdmin = computed(() => authStore.user?.rol === "administrador");

async function cargarMisPagos() {
  try {
    const resp = await api.get("/pagos/mis-pagos");
    misPagos.value = resp.data || [];
  } catch {}
}

async function cargarEmpleados() {
  if (!esAdmin.value) return;
  try {
    const resp = await api.get("/usuarios/", { params: { rol: "empleado", page_size: 100 } });
    empleados.value = resp.data?.items || [];
  } catch {}
}

async function cargarPendientes() {
  try {
    const params: any = {};
    if (esAdmin.value && empleadoSel.value) params.id_usuario = empleadoSel.value;
    const response = await api.get("/pagos/turnos-pendientes", { params });
    turnosPendientes.value = response.data || [];
  } catch {}
}

async function marcarRecibido(idPago: number) {
  try {
    await api.patch(`/pagos/${idPago}/marcar-recibido`);
    await cargarMisPagos();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error");
  }
}

onMounted(async () => {
  await cargarEmpleados();
  await cargarPendientes();
  await cargarMisPagos();
  loading.value = false;
});

const totalSeleccionado = computed(() =>
  turnosPendientes.value
    .filter((t) => selected.value.has(t.id_turno))
    .reduce((sum, t) => sum + t.valor_total_turno, 0)
);

function toggle(id: number) {
  if (selected.value.has(id)) selected.value.delete(id);
  else selected.value.add(id);
}

async function procesarPago(metodo: string) {
  if (selected.value.size === 0 || !empleadoSel.value) return;
  try {
    await api.post("/pagos/", {
      id_usuario_receptor: empleadoSel.value,
      metodo_pago: metodo,
      turnos_ids: Array.from(selected.value),
    });
    alert("Pago procesado");
    selected.value.clear();
    await cargarPendientes();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error");
  }
}

watch(empleadoSel, () => {
  selected.value.clear();
  cargarPendientes();
});
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Mis Pagos</h1>
      <router-link to="/" class="btn-back">Volver</router-link>
    </header>
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <div class="card" style="margin-bottom: 16px;">
        <h3>Mis pagos recibidos</h3>
        <div v-if="misPagos.length === 0" class="muted">No tienes pagos registrados</div>
        <div v-for="pago in misPagos" :key="pago.id_pago" class="turno-row">
          <div class="turno-info">
            <span>{{ new Date(pago.fecha_pago).toLocaleDateString() }} - ${{ Number(pago.monto_total).toLocaleString() }}</span>
            <span :class="pago.recibido_empleado ? 'ok' : 'negative'">
              {{ pago.recibido_empleado ? 'Recibido' : 'Pendiente' }}
            </span>
          </div>
          <button v-if="!pago.recibido_empleado" class="primary" @click="marcarRecibido(pago.id_pago)">Marcar recibido</button>
        </div>
      </div>
      <div v-if="esAdmin" class="card" style="margin-bottom: 16px;">
        <label>Empleado</label>
        <select v-model.number="empleadoSel">
          <option :value="null">Seleccione empleado</option>
          <option v-for="e in empleados" :key="e.id_usuario" :value="e.id_usuario">
            {{ e.nombre_completo }}
          </option>
        </select>
      </div>
      <div v-if="turnosPendientes.length === 0" class="empty">No hay turnos pendientes por cobrar</div>
      <div v-else>
        <div v-for="turno in turnosPendientes" :key="turno.id_turno" class="turno-row card" @click="esAdmin ? toggle(turno.id_turno) : null">
          <input v-if="esAdmin" type="checkbox" :checked="selected.has(turno.id_turno)" />
          <div class="turno-info">
            <span>{{ turno.fecha }} | {{ turno.hora_inicio }} - {{ turno.hora_fin }}</span>
            <span class="turno-valor">${{ turno.valor_total_turno.toLocaleString() }}</span>
          </div>
        </div>
        <div v-if="esAdmin" class="payment-bar">
          <span class="total-label">Seleccionados: {{ selected.size }} | Total: ${{ totalSeleccionado.toLocaleString() }}</span>
          <div class="payment-actions">
            <button @click="procesarPago('efectivo')" class="primary">Efectivo</button>
            <button @click="procesarPago('transferencia')" class="primary">Transferencia</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.btn-back { color: var(--accent); text-decoration: none; }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 40px; }
.turno-row { display: flex; align-items: center; gap: 12px; cursor: pointer; margin-bottom: 8px; }
.turno-row:hover { border-color: var(--accent); }
.turno-info { display: flex; justify-content: space-between; flex: 1; }
.turno-valor { font-weight: 700; color: var(--accent); }
.payment-bar { position: fixed; bottom: 0; left: 0; right: 0; background: var(--primary); border-top: 1px solid var(--border); padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
.total-label { font-weight: 600; }
.payment-actions { display: flex; gap: 8px; }
</style>
