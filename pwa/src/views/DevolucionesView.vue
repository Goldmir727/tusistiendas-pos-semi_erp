<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../api/client";

const devoluciones = ref<any[]>([]);
const ventas = ref<any[]>([]);
const loading = ref(true);
const registrar = ref(false);
const ventaSel = ref<number | null>(null);
const motivo = ref("");
const detalle = ref<any[]>([]);

async function cargar() {
  loading.value = true;
  try {
    const [devs, ventasResp] = await Promise.all([
      api.get("/devoluciones"),
      api.get("/ventas", { params: { page_size: 50 } }),
    ]);
    devoluciones.value = devs.data;
    ventas.value = ventasResp.data.items;
  } finally {
    loading.value = false;
  }
}

async function agregarProductoVenta() {
  const v = ventas.value.find((x) => x.id_venta === ventaSel.value);
  if (!v) return;
  detalle.value = v.detalles.map((d: any) => ({
    id_producto: d.id_producto,
    cantidad: 1,
    precio_unitario: d.precio_unitario,
    iva_porcentaje: 19,
    // nombre para mostrar
    nombre: d.id_producto,
  }));
}

async function guardar() {
  if (!ventaSel.value || detalle.value.length === 0) return;
  try {
    const response = await api.post("/devoluciones", {
      id_venta: ventaSel.value,
      motivo: motivo.value || null,
      detalles: detalle.value.map((d: any) => ({
        id_producto: d.id_producto,
        cantidad: d.cantidad,
        precio_unitario: d.precio_unitario,
        iva_porcentaje: d.iva_porcentaje,
      })),
    });
    const estado = response.data.estado;
    alert(estado === "aprobada" ? "Devolucion aprobada automaticamente" : "Devolucion enviada para aprobacion");
    registrar.value = false;
    detalle.value = [];
    ventaSel.value = null;
    motivo.value = "";
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al registrar devolucion");
  }
}

async function aprobar(id: number) {
  try {
    await api.post(`/devoluciones/${id}/aprobar`);
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al aprobar");
  }
}

async function rechazar(id: number) {
  try {
    await api.post(`/devoluciones/${id}/rechazar`);
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al rechazar");
  }
}

onMounted(cargar);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Devoluciones</h1>
      <div class="header-actions">
        <router-link to="/" class="btn-back">Volver</router-link>
        <button @click="registrar = true" class="primary">Nueva Devolucion</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <div v-if="devoluciones.length === 0" class="empty">No hay devoluciones registradas</div>
      <div v-for="d in devoluciones" :key="d.id_devolucion" class="dev-row card">
        <div class="dev-info">
          <span class="dev-id">Devolucion #{{ d.id_devolucion }} (Venta #{{ d.id_venta }})</span>
          <span class="muted">{{ new Date(d.fecha).toLocaleDateString() }} | {{ d.motivo || "Sin motivo" }}</span>
        </div>
        <div class="dev-actions">
          <span class="estado" :class="`estado-${d.estado}`">{{ d.estado.replace("_", " ") }}</span>
          <span class="monto">${{ d.monto.toLocaleString() }}</span>
          <button v-if="d.estado === 'pendiente_aprobacion'" @click="aprobar(d.id_devolucion)" class="primary btn-sm">Aprobar</button>
          <button v-if="d.estado === 'pendiente_aprobacion'" @click="rechazar(d.id_devolucion)" class="danger btn-sm">Rechazar</button>
        </div>
      </div>
    </div>

    <div v-if="registrar" class="modal-overlay" @click.self="registrar = false">
      <div class="modal wide">
        <h3>Nueva Devolucion</h3>
        <label>Venta</label>
        <select v-model.number="ventaSel">
          <option :value="null">Seleccionar venta...</option>
          <option v-for="v in ventas" :key="v.id_venta" :value="v.id_venta">
            Venta #{{ v.id_venta }} - ${{ v.total.toLocaleString() }} - {{ new Date(v.fecha_venta).toLocaleDateString() }}
          </option>
        </select>
        <div v-if="ventaSel && ventas.find((v) => v.id_venta === ventaSel)">
          <h4>Items de la venta</h4>
          <div v-for="det in ventas.find((v) => v.id_venta === ventaSel).detalles" :key="det.id_detalle" class="detalle-row">
            <span>Producto #{{ det.id_producto }} x{{ det.cantidad }}</span>
            <span class="muted">${{ det.precio_unitario.toLocaleString() }}</span>
          </div>
          <button @click="agregarProductoVenta" class="primary btn-fill">Copiar items al detalle de devolucion</button>
        </div>
        <label>Motivo</label>
        <input v-model="motivo" placeholder="Ej: producto vencido, error de caja" />
        <h4>Detalle devolucion</h4>
        <div v-for="(d, index) in detalle" :key="d.id_producto" class="detalle-row">
          <span>Producto #{{ d.id_producto }}</span>
          <input v-model.number="d.cantidad" type="number" min="1" class="cantidad-input" />
          <button @click="detalle.splice(index, 1)" class="danger btn-sm">X</button>
        </div>
        <div class="modal-actions">
          <button @click="guardar" class="primary" :disabled="!ventaSel || detalle.length === 0">Guardar</button>
          <button @click="registrar = false" class="secondary">Cancelar</button>
        </div>
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
.loading, .empty { text-align: center; color: var(--text-muted); padding: 40px; }
.dev-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 8px; padding: 12px; }
.dev-info { display: flex; flex-direction: column; }
.dev-actions { display: flex; align-items: center; gap: 12px; }
.estado { padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.estado-aprobada { background: #16321c; color: var(--accent); }
.estado-pendiente_aprobacion { background: #33280f; color: var(--warning); }
.estado-rechazada { background: #331414; color: var(--danger); }
.monto { font-weight: 700; color: var(--accent); }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.danger { background: var(--danger); color: white; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; width: 100%; max-width: 400px; }
.modal.wide { max-width: 620px; }
.modal label { display: block; font-size: 12px; color: var(--text-muted); margin: 10px 0 4px; }
.modal select, .modal input { width: 100%; }
.detalle-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border); }
.cantidad-input { width: 80px; }
.modal-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>