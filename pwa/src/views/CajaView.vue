<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import api from "../api/client";

const sesion = ref<any | null>(null);
const panel = ref<any | null>(null);
const puntos = ref<any[]>([]);
const historial = ref<any[]>([]);
const empleados = ref<any[]>([]);

async function cargarEmpleados() {
  if (!puntoSel.value) { empleados.value = []; return; }
  try {
    const resp = await api.get("/caja/empleados-disponibles", { params: { id_punto_venta: puntoSel.value } });
    empleados.value = resp.data || [];
    if (empleados.value.length === 1) empleadoSel.value = empleados.value[0].id_usuario;
  } catch {
    empleados.value = [];
  }
}
const loading = ref(true);
const error = ref("");

const baseInicial = ref(50000);
const puntoSel = ref<number | null>(null);
const empleadoSel = ref<number | null>(null);
const abriendo = ref(false);

watch(puntoSel, () => {
  empleadoSel.value = null;
  cargarEmpleados();
});
const arqueo = ref<Record<string, number>>({});
const egreso = ref({ categoria: "general", descripcion: "", monto: 0 });
const cierre = ref<any | null>(null);

const DENOMINACIONES = [
  { key: "billete_50000", label: "Billete $50.000", valor: 50000 },
  { key: "billete_20000", label: "Billete $20.000", valor: 20000 },
  { key: "billete_10000", label: "Billete $10.000", valor: 10000 },
  { key: "billete_5000", label: "Billete $5.000", valor: 5000 },
  { key: "billete_2000", label: "Billete $2.000", valor: 2000 },
  { key: "billete_1000", label: "Billete $1.000", valor: 1000 },
  { key: "moneda_500", label: "Moneda $500", valor: 500 },
  { key: "moneda_200", label: "Moneda $200", valor: 200 },
  { key: "moneda_100", label: "Moneda $100", valor: 100 },
  { key: "moneda_50", label: "Moneda $50", valor: 50 },
];

const totalContado = computed(() =>
  DENOMINACIONES.reduce((suma, d) => suma + d.valor * (arqueo.value[d.key] || 0), 0)
);
const diferencia = computed(() => {
  if (!panel.value) return 0;
  return totalContado.value - Number(panel.value.efectivo_real_esperado);
});

function money(valor: number | string | null | undefined) {
  return Number(valor || 0).toLocaleString("es-CO");
}

async function cargar() {
  loading.value = true;
  error.value = "";
  try {
    const [abierta, pts, hist] = await Promise.all([
      api.get("/caja/abierta"),
      api.get("/caja/puntos"),
      api.get("/caja/historial", { params: { limit: 10 } }),
    ]);
    sesion.value = abierta.data;
    puntos.value = pts.data;
    historial.value = hist.data;
    if (puntos.value.length === 1 && !puntoSel.value) {
      puntoSel.value = puntos.value[0].id_punto_venta;
      await cargarEmpleados();
    }
    if (!puntoSel.value && puntos.value.length > 0) {
      puntoSel.value = puntos.value[0].id_punto_venta;
    }
    if (sesion.value) {
      const resp = await api.get("/caja/panel");
      panel.value = resp.data;
    } else {
      panel.value = null;
    }
  } catch (e: any) {
    error.value = e.response?.data?.error?.message || "No se pudo cargar la caja";
  } finally {
    loading.value = false;
  }
}

async function abrir() {
  if (abriendo.value) return;
  const punto = puntos.value.find((p) => p.id_punto_venta === puntoSel.value);
  if (!punto) return;
  if (!empleadoSel.value) {
    alert("Seleccione el empleado que abre la caja");
    return;
  }
  abriendo.value = true;
  try {
    await api.post("/caja/abrir", {
      base_inicial: baseInicial.value,
      id_sucursal: punto.id_sucursal,
      id_punto_venta: punto.id_punto_venta,
      id_usuario_abre_caja: empleadoSel.value,
    });
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "No se pudo abrir la caja");
    // Si la caja ya estaba abierta, refrescar para mostrar la sesión activa.
    await cargar();
  } finally {
    abriendo.value = false;
  }
}

async function registrarEgreso() {
  if (!sesion.value || egreso.value.monto <= 0 || !egreso.value.descripcion) return;
  try {
    await api.post("/egresos/", {
      id_sesion_caja: sesion.value.id_sesion_caja,
      id_sucursal: sesion.value.id_sucursal,
      categoria: egreso.value.categoria,
      descripcion: egreso.value.descripcion,
      monto: egreso.value.monto,
    });
    egreso.value = { categoria: "general", descripcion: "", monto: 0 };
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "No se pudo registrar el egreso");
  }
}

async function cerrar() {
  if (!sesion.value) return;
  const confirmado = confirm(
    `¿Cerrar la caja con $${money(totalContado.value)} contados?\n` +
      `Esperado: $${money(panel.value?.efectivo_real_esperado)}`
  );
  if (!confirmado) return;
  try {
    const resp = await api.post("/caja/cerrar", {
      arqueo: DENOMINACIONES.filter((d) => (arqueo.value[d.key] || 0) > 0).map((d) => ({
        denominacion: d.key,
        cantidad: arqueo.value[d.key],
      })),
    });
    cierre.value = resp.data;
    arqueo.value = {};
    await cargar();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "No se pudo cerrar la caja");
  }
}

onMounted(cargar);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>Caja</h1>
      <router-link to="/" class="btn-back">Volver</router-link>
    </header>

    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else-if="error" class="empty">{{ error }}</div>

    <template v-else>
      <div v-if="!sesion" class="card">
        <h3>Abrir caja</h3>
        <p class="muted">Sin caja abierta no se pueden registrar ventas.</p>
        <div v-if="puntos.length > 1">
          <label>Punto de venta</label>
          <select v-model.number="puntoSel">
            <option v-for="p in puntos" :key="p.id_punto_venta" :value="p.id_punto_venta">
              {{ p.sucursal }} - {{ p.nombre }}
            </option>
          </select>
        </div>
        <div v-else-if="puntos.length === 1" class="muted" style="margin-bottom: 8px;">
          Caja: {{ puntos[0].sucursal }} - {{ puntos[0].nombre }}
        </div>
        <label>Empleado que abre caja</label>
        <select v-model.number="empleadoSel">
          <option :value="null">Seleccione empleado</option>
          <option v-for="e in empleados" :key="e.id_usuario" :value="e.id_usuario">
            {{ e.nombre_completo }} ({{ e.hora_inicio }} - {{ e.hora_fin }})
          </option>
        </select>
        <label>Base inicial</label>
        <input v-model.number="baseInicial" type="number" min="0" />
        <button class="primary btn-block" :disabled="abriendo" @click="abrir">
          {{ abriendo ? "Abriendo..." : "Abrir caja" }}
        </button>
      </div>

      <template v-else>
        <div v-if="panel" class="desglose">
          <div class="card stat">
            <span class="stat-label">Base inicial</span>
            <span class="stat-value">${{ money(panel.base_inicial) }}</span>
          </div>
          <div class="card stat">
            <span class="stat-label">Ventas efectivo</span>
            <span class="stat-value">${{ money(panel.ventas_efectivo_acumulado) }}</span>
          </div>
          <div class="card stat">
            <span class="stat-label">Abonos efectivo</span>
            <span class="stat-value positive">+${{ money(panel.abonos_efectivo) }}</span>
          </div>
          <div class="card stat">
            <span class="stat-label">Devoluciones efectivo</span>
            <span class="stat-value negative">-${{ money(panel.devoluciones_efectivo) }}</span>
          </div>
          <div class="card stat">
            <span class="stat-label">Egresos</span>
            <span class="stat-value negative">-${{ money(panel.egresos) }}</span>
          </div>
          <div class="card stat destacado">
            <span class="stat-label">Efectivo esperado</span>
            <span class="stat-value">${{ money(panel.efectivo_real_esperado) }}</span>
          </div>
        </div>

        <div class="grid-2">
          <div class="card">
            <h3>Registrar egreso</h3>
            <label>Categoría</label>
            <select v-model="egreso.categoria">
              <option>general</option>
              <option>renta</option>
              <option>servicios</option>
              <option>insumos</option>
              <option>retiro</option>
            </select>
            <label>Descripción</label>
            <input v-model="egreso.descripcion" placeholder="Ej: bolsas, domicilio" />
            <label>Monto</label>
            <input v-model.number="egreso.monto" type="number" min="1" />
            <button class="primary btn-block" @click="registrarEgreso">Guardar egreso</button>
          </div>

          <div class="card">
            <h3>Arqueo de cierre</h3>
            <div class="arqueo">
              <div v-for="d in DENOMINACIONES" :key="d.key" class="arqueo-row">
                <span>{{ d.label }}</span>
                <input v-model.number="arqueo[d.key]" type="number" min="0" placeholder="0" />
                <span class="muted">${{ money(d.valor * (arqueo[d.key] || 0)) }}</span>
              </div>
            </div>
            <div class="totales">
              <div>Contado: <strong>${{ money(totalContado) }}</strong></div>
              <div>
                Diferencia:
                <strong :class="diferencia === 0 ? 'ok' : 'negative'">${{ money(diferencia) }}</strong>
              </div>
            </div>
            <button class="danger btn-block" @click="cerrar">Cerrar caja</button>
          </div>
        </div>
      </template>

      <div v-if="cierre" class="card cierre">
        <h3>Cierre de la sesión #{{ cierre.id_sesion_caja }}</h3>
        <p>
          Contado: <strong>${{ money(cierre.efectivo_declarado_cierre) }}</strong> ·
          Descuadre:
          <strong :class="Number(cierre.descuadre) === 0 ? 'ok' : 'negative'">
            ${{ money(cierre.descuadre) }}
          </strong>
        </p>
      </div>

      <div class="card">
        <h3>Últimos cierres</h3>
        <div v-if="historial.length === 0" class="muted">Todavía no hay cierres.</div>
        <div v-for="h in historial" :key="h.id_sesion_caja" class="hist-row">
          <span class="muted">{{ new Date(h.fecha_cierre).toLocaleString() }}</span>
          <span>Base ${{ money(h.base_inicial) }}</span>
          <span class="positive">+${{ money(h.ventas_efectivo) }}</span>
          <span class="negative">-${{ money(h.total_egresos) }}</span>
          <span :class="Number(h.descuadre) === 0 ? 'ok' : 'negative'">
            Descuadre ${{ money(h.descuadre) }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1000px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.btn-back { color: var(--accent); text-decoration: none; }
.muted { color: var(--text-muted); font-size: 12px; }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 40px; }
label { display: block; font-size: 12px; color: var(--text-muted); margin: 10px 0 4px; }
h3 { margin-bottom: 8px; }
.desglose { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.stat { text-align: center; padding: 14px; }
.stat-label { display: block; color: var(--text-muted); font-size: 12px; margin-bottom: 6px; }
.stat-value { font-size: 18px; font-weight: 700; }
.destacado { border-color: var(--accent); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.arqueo { max-height: 240px; overflow-y: auto; }
.arqueo-row { display: grid; grid-template-columns: 1fr 80px 90px; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }
.totales { display: flex; justify-content: space-between; margin: 12px 0; font-size: 14px; }
.btn-block { width: 100%; margin-top: 12px; }
.danger { background: var(--danger); color: white; }
.ok { color: var(--success); }
.positive { color: var(--success); }
.negative { color: var(--danger); }
.cierre { margin-bottom: 16px; border-color: var(--success); }
.hist-row { display: flex; justify-content: space-between; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
@media (max-width: 720px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
