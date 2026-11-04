<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../api/client";

const clientes = ref<any[]>([]);
const q = ref("");
const loading = ref(true);
const cuentaAbierta = ref<any | null>(null);
const abonoVenta = ref<number | null>(null);
const abonoMonto = ref(0);
const mostrarNuevo = ref(false);
const nuevo = ref({ nombre: "", numero_doc: "", tipo_doc: "CC", telefono: "", email: "", direccion: "", regimen_fiscal: "" });

async function cargar() {
  loading.value = true;
  try {
    const response = await api.get("/clientes", { params: { q: q.value || undefined, page_size: 100 } });
    clientes.value = response.data.items;
  } finally {
    loading.value = false;
  }
}

async function crearCliente() {
  try {
    await api.post("/clientes", nuevo.value);
    mostrarNuevo.value = false;
    nuevo.value = { nombre: "", numero_doc: "", tipo_doc: "CC", telefono: "", email: "", direccion: "", regimen_fiscal: "" };
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al crear cliente");
  }
}

async function verCuenta(id: number) {
  try {
    const response = await api.get(`/clientes/${id}/cuenta`);
    cuentaAbierta.value = response.data;
  } catch {}
}

async function registrarAbono() {
  if (!cuentaAbierta.value || abonoMonto.value <= 0) return;
  try {
    await api.post("/clientes/abonos", {
      id_cliente: cuentaAbierta.value.id_cliente,
      id_venta: abonoVenta.value || null,
      monto: abonoMonto.value,
    });
    abonoMonto.value = 0;
    abonoVenta.value = null;
    await verCuenta(cuentaAbierta.value.id_cliente);
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al registrar abono");
  }
}

onMounted(cargar);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Clientes y Fiado</h1>
      <div class="header-actions">
        <router-link to="/" class="btn-back">Volver</router-link>
        <button @click="mostrarNuevo = true" class="primary">Nuevo Cliente</button>
      </div>
    </header>

    <div class="toolbar card">
      <input v-model="q" @keyup.enter="cargar" placeholder="Buscar por nombre, documento o telefono" />
      <button @click="cargar" class="primary">Buscar</button>
    </div>

    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <div v-if="clientes.length === 0" class="empty">No hay clientes registrados</div>
      <div v-for="c in clientes" :key="c.id_cliente" class="cliente-row card">
        <div class="cliente-info">
          <span class="cliente-name">{{ c.nombre }}</span>
          <span class="muted">{{ c.tipo_doc }} {{ c.numero_doc }} {{ c.telefono }}</span>
        </div>
        <div class="cliente-actions">
          <span class="saldo" :class="{ deudor: c.saldo_deudor > 0 }">
            {{ c.saldo_deudor > 0 ? `Fiado: $${c.saldo_deudor.toLocaleString()}` : "Sin deuda" }}
          </span>
          <button @click="verCuenta(c.id_cliente)" class="secondary">Cuenta</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarNuevo" class="modal-overlay" @click.self="mostrarNuevo = false">
      <div class="modal">
        <h3>Nuevo Cliente</h3>
        <label>Nombre</label>
        <input v-model="nuevo.nombre" required />
        <label>{{ nuevo.tipo_doc === "CC" ? "Cedula" : "Documento" }}</label>
        <input v-model="nuevo.numero_doc" />
        <div class="row-2">
          <div>
            <label>Tipo doc</label>
            <select v-model="nuevo.tipo_doc">
              <option>CC</option>
              <option>NIT</option>
              <option>CE</option>
              <option>Pasaporte</option>
            </select>
          </div>
          <div>
            <label>Telefono</label>
            <input v-model="nuevo.telefono" />
          </div>
        </div>
        <div class="row-2">
          <div>
            <label>Email</label>
            <input v-model="nuevo.email" />
          </div>
          <div>
            <label>Direccion</label>
            <input v-model="nuevo.direccion" />
          </div>
        </div>
        <label>Regimen fiscal</label>
        <select v-model="nuevo.regimen_fiscal">
          <option value="">Seleccionar...</option>
          <option value="regimen_simplificado">Regimen simplificado</option>
          <option value="regimen_comun">Regimen comun</option>
          <option value="responsable_iva">Responsable de IVA</option>
        </select>
        <div class="modal-actions">
          <button @click="crearCliente" class="primary">Guardar</button>
          <button @click="mostrarNuevo = false" class="secondary">Cancelar</button>
        </div>
      </div>
    </div>

    <div v-if="cuentaAbierta" class="modal-overlay" @click.self="cuentaAbierta = false">
      <div class="modal wide">
        <h3>Cuenta: {{ cuentaAbierta.nombre }}</h3>
        <p class="saldo-grande">Saldo deudor: <strong>${{ cuentaAbierta.saldo_deudor.toLocaleString() }}</strong></p>
        <h4>Ventas pendientes</h4>
        <div v-for="v in cuentaAbierta.ventas_pendientes" :key="v.id_venta" class="fila">
          <span class="muted">{{ new Date(v.fecha).toLocaleDateString() }}</span>
          <span>Pendiente: ${{ (v.total - v.monto_abonado - v.monto_devuelto).toLocaleString() }}</span>
          <button @click="abonoVenta = v.id_venta" class="btn-sm">Abonar</button>
        </div>
        <h4>Registrar abono</h4>
        <div class="abono-bar">
          <input v-model.number="abonoMonto" type="number" placeholder="Monto" />
          <button @click="registrarAbono" class="primary">Abonar</button>
        </div>
        <h4>Abonos historicos</h4>
        <div v-for="a in cuentaAbierta.abonos" :key="a.id_abono" class="fila-row">
          <span class="muted">{{ new Date(a.fecha).toLocaleDateString() }}</span>
          <span>${{ a.monto.toLocaleString() }}<span v-if="a.observacion" class="muted"> - {{ a.observacion }}</span></span>
        </div>
        <button @click="cuentaAbierta = false" class="secondary">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-actions { display: flex; gap: 12px; align-items: center; }
.btn-back { color: var(--accent); text-decoration: none; }
.muted { color: var(--text-muted); font-size: 12px; }
.toolbar { display: flex; gap: 8px; padding: 12px; margin-bottom: 16px; }
.toolbar input { flex: 1; }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 40px; }
.cliente-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 8px; padding: 12px; }
.cliente-name { font-weight: 600; display: block; }
.cliente-actions { display: flex; align-items: center; gap: 12px; }
.saldo { font-weight: 700; }
.saldo.deudor { color: var(--warning); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; width: 100%; max-width: 400px; }
.modal.wide { max-width: 600px; }
.modal label { display: block; font-size: 12px; color: var(--text-muted); margin: 10px 0 4px; }
.modal input, .modal select { width: 100%; }
.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-actions { display: flex; gap: 8px; margin-top: 16px; }
.fila-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); }
.abono-bar { display: flex; gap: 8px; margin: 8px 0; }
.saldo-grande { font-size: 18px; }
</style>