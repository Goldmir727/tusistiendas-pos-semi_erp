<script setup lang="ts">
import { ref } from "vue";
import api from "../api/client";

const proveedores = ref<any[]>([]);
const productos = ref<any[]>([]);
const compras = ref<any[]>([]);
const loading = ref(true);
const registrar = ref(false);
const idProveedorSel = ref<number | null>(null);
const lineaSel = ref<number | null>(null);
const lineaCant = ref(1);
const lineaCosto = ref(0);
const detalle = ref<any[]>([]);
const idSucursal = ref(1);
const nuevoProveedor = ref({ nombre: "", nit: "", telefono: "", email: "", direccion: "" });
const mostrarProveedorModal = ref(false);

async function cargarTodo() {
  loading.value = true;
  try {
    const [prov, prod, comp] = await Promise.all([
      api.get("/compras/proveedores"),
      api.get("/productos", { params: { page_size: 100 } }),
      api.get("/compras", { params: { page_size: 50 } }),
    ]);
    proveedores.value = prov.data;
    productos.value = prod.data.items;
    compras.value = comp.data.items;
  } finally {
    loading.value = false;
  }
}

async function crearProveedor() {
  try {
    await api.post("/compras/proveedores", nuevoProveedor.value);
    mostrarProveedorModal.value = false;
    nuevoProveedor.value = { nombre: "", nit: "", telefono: "", email: "", direccion: "" };
    const prov = await api.get("/compras/proveedores");
    proveedores.value = prov.data;
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al crear proveedor");
  }
}

function agregarLinea() {
  const prod = productos.value.find((p) => p.id_producto === lineaSel.value);
  if (!prod) return;
  const existente = detalle.value.find((d) => d.id_producto === lineaSel.value);
  if (existente) {
    existente.cantidad += Number(lineaCant.value);
  } else {
    detalle.value.push({
      id_producto: prod.id_producto,
      nombre: prod.nombre_producto,
      cantidad: Number(lineaCant.value),
      costo_unitario: Number(lineaCosto.value) || Number(prod.precio_venta),
    });
  }
  lineaSel.value = null;
  lineaCant.value = 1;
  lineaCosto.value = 0;
}

async function guardarCompra() {
  if (!idProveedorSel.value || detalle.value.length === 0) return;
  try {
    await api.post("/compras", {
      id_proveedor: idProveedorSel.value,
      id_sucursal: idSucursal.value,
      detalles: detalle.value.map((d) => ({
        id_producto: d.id_producto,
        cantidad: d.cantidad,
        costo_unitario: d.costo_unitario,
      })),
    });
    detalle.value = [];
    lineaSel.value = null;
    registrar.value = false;
    await cargarTodo();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al registrar compra");
  }
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Compras e Inventario</h1>
      <div class="header-actions">
        <router-link to="/" class="btn-back">Volver</router-link>
        <button @click="registrar = true" class="primary">Registrar Compra</button>
        <button @click="mostrarProveedorModal = true" class="secondary">Nuevo Proveedor</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else>
      <h2>Proveedores</h2>
      <div class="proveedores-row">
        <span v-if="proveedores.length === 0" class="muted">Sin proveedores registrados</span>
        <span v-for="p in proveedores" :key="p.id_proveedor" class="proveedor-chip">{{ p.nombre }}</span>
      </div>

      <h2>Historial de compras</h2>
      <div v-if="compras.length === 0" class="empty">No hay compras registradas</div>
      <div v-for="c in compras" :key="c.id_compra" class="compra-row card">
        <div>
          <span class="muted">{{ new Date(c.fecha_compra).toLocaleDateString() }}</span>
          <div class="det">{{ c.detalles.length }} productos | Total: ${{ c.total.toLocaleString() }}</div>
        </div>
      </div>
    </div>

    <div v-if="registrar" class="modal-overlay" @click.self="registrar = false">
      <div class="modal wide">
        <h3>Registrar Compra</h3>
        <label>Proveedor</label>
        <select v-model.number="idProveedorSel">
          <option :value="null">Seleccionar...</option>
          <option v-for="p in proveedores" :key="p.id_proveedor" :value="p.id_proveedor">{{ p.nombre }}</option>
        </select>
        <h4>Agregar producto</h4>
        <div class="linea-compra">
          <select v-model.number="lineaSel">
            <option :value="null">Seleccionar producto...</option>
            <option v-for="p in productos" :key="p.id_producto" :value="p.id_producto">{{ p.nombre_producto }}</option>
          </select>
          <input v-model.number="lineaCant" type="number" min="1" placeholder="Cant" />
          <input v-model.number="lineaCosto" type="number" min="0" placeholder="Costo" />
          <button @click="agregarLinea" class="primary">+</button>
        </div>
        <div v-for="d in detalle" :key="d.id_producto" class="detalle-row">
          <span>{{ d.nombre }}</span>
          <span class="muted">x{{ d.cantidad }} @ ${{ d.costo_unitario.toLocaleString() }}</span>
        </div>
        <div class="modal-actions">
          <button @click="guardarCompra" class="primary" :disabled="!idProveedorSel || detalle.length === 0">Guardar</button>
          <button @click="registrar = false" class="secondary">Cancelar</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarProveedorModal" class="modal-overlay" @click.self="mostrarProveedorModal = false">
      <div class="modal">
        <h3>Nuevo Proveedor</h3>
        <label>Nombre</label>
        <input v-model="nuevoProveedor.nombre" required />
        <label>NIT</label>
        <input v-model="nuevoProveedor.nit" />
        <div class="row-2">
          <div><label>Telefono</label><input v-model="nuevoProveedor.telefono" /></div>
          <div><label>Email</label><input v-model="nuevoProveedor.email" /></div>
        </div>
        <label>Direccion</label>
        <input v-model="nuevoProveedor.direccion" />
        <div class="modal-actions">
          <button @click="crearProveedor" class="primary">Guardar</button>
          <button @click="mostrarProveedorModal = false" class="secondary">Cancelar</button>
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
.proveedores-row { margin-bottom: 24px; }
.proveedor-chip { display: inline-block; background: var(--primary-light); border: 1px solid var(--border); border-radius: 4px; padding: 6px 12px; margin: 4px 6px 4px 0; }
.compra-row { padding: 12px; margin-bottom: 8px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; width: 100%; max-width: 400px; }
.modal.wide { max-width: 620px; }
.modal label { display: block; font-size: 12px; color: var(--text-muted); margin: 10px 0 4px; }
.modal select, .modal input { width: 100%; }
.linea-compra { display: grid; grid-template-columns: 1fr 80px 100px 40px; gap: 8px; margin: 8px 0; }
.detalle-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
.modal-actions { display: flex; gap: 8px; margin-top: 16px; }
.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>