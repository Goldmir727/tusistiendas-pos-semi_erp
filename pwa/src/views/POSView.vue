<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/client";
import { normalizarEscaneo } from "../lib/scan";
import { imprimirTiquete, imprimirTiqueteLocal } from "../lib/ticket";
import { useAuthStore } from "../stores/auth";
import { usePOSStore, type MedioPago, type PagoLinea } from "../stores/pos";

const router = useRouter();
const pos = usePOSStore();
const auth = useAuthStore();

const scanRef = ref<HTMLInputElement | null>(null);
const codigo = ref("");
const mensajeEscaneo = ref("");
const errorEscaneo = ref(false);

const showPago = ref(false);
const showCliente = ref(false);
const temporalAEliminar = ref<string | null>(null);
const descripcionTemporal = ref("");

const ventaFinal = ref<{ uuid: string; total: number; cambio: number; offline: boolean; mensaje?: string } | null>(null);

const busquedaCliente = ref("");
const clientes = ref<{ id_cliente: number; nombre: string; numero_doc: string }[]>([]);
const buscandoCliente = ref(false);

const pagos = ref<PagoLinea[]>([]);
const medioSeleccionado = ref<MedioPago | null>(null);
const montoPago = ref<number | null>(null);
const recibidoEfectivo = ref<number | null>(null);
const errorPago = ref("");
const cobrando = ref(false);

const total = computed(() => pos.totales.total);
const pagado = computed(() => pagos.value.reduce((suma, pago) => suma + pago.monto, 0));
const restante = computed(() => Math.max(0, total.value - pagado.value));
const cambio = computed(() =>
  pagos.value
    .filter((pago) => pago.tipo === "efectivo")
    .reduce((suma, pago) => suma + Math.max(0, (pago.monto_recibido ?? pago.monto) - pago.monto), 0),
);
const usaFiado = computed(() => pagos.value.some((pago) => pago.tipo === "fiado"));
const puedeCobrar = computed(
  () => pagos.value.length > 0 && restante.value <= 0.01 && (!usaFiado.value || pos.idCliente !== null),
);

function enfocar() {
  void nextTick(() => scanRef.value?.focus());
}

function formatear(valor: number): string {
  return Math.round(valor).toLocaleString("es-CO");
}

async function escanear() {
  const resultado = normalizarEscaneo(codigo.value);
  codigo.value = "";

  if (!resultado.ok) {
    if (resultado.motivo) {
      errorEscaneo.value = true;
      mensajeEscaneo.value = resultado.motivo;
    }
    enfocar();
    return;
  }

  const agregado = await pos.agregarPorCodigo(resultado.codigo as string);
  errorEscaneo.value = !agregado.ok;
  mensajeEscaneo.value = agregado.ok ? "" : agregado.motivo ?? "No se pudo agregar el producto";
  enfocar();
}

function nuevaVenta() {
  pos.limpiarVenta();
  mensajeEscaneo.value = "";
  errorEscaneo.value = false;
  enfocar();
}

async function guardarTemporal() {
  if (pos.carrito.length === 0) return;
  await pos.guardarTemporal(undefined, descripcionTemporal.value || null);
  descripcionTemporal.value = "";
  mensajeEscaneo.value = "";
  enfocar();
}

async function abrirTemporal(id: string) {
  await pos.abrirTemporal(id);
  enfocar();
}

function puedeEditarDescripcion(temporal: any): boolean {
  if (!pos.sesionCaja || pos.sesionCaja.estado !== "abierta") return false;
  const rol = auth.user?.rol;
  if (rol === "administrador") return true;
  const opener = pos.sesionCaja.id_usuario_abre_caja;
  return auth.user?.id_usuario === opener || auth.user?.id_usuario === temporal.id_usuario_creador;
}

async function confirmarEliminarTemporal() {
  if (!temporalAEliminar.value) return;
  await pos.eliminarTemporal(temporalAEliminar.value);
  temporalAEliminar.value = null;
}

function abrirModalPago() {
  if (pos.carrito.length === 0) return;
  if (!pos.sesionCaja) {
    errorEscaneo.value = true;
    mensajeEscaneo.value = "La caja está cerrada. Ábrela desde el módulo Caja para poder cobrar.";
    return;
  }
  pagos.value = [];
  errorPago.value = "";
  medioSeleccionado.value = pos.medios[0] ?? null;
  montoPago.value = total.value;
  recibidoEfectivo.value = null;
  showPago.value = true;
}

function elegirMedio(medio: MedioPago) {
  medioSeleccionado.value = medio;
  montoPago.value = restante.value > 0 ? restante.value : total.value;
  recibidoEfectivo.value = null;
  errorPago.value = "";
}

function agregarPago() {
  const medio = medioSeleccionado.value;
  if (!medio) return;

  const monto = Number(montoPago.value ?? restante.value);
  if (!Number.isFinite(monto) || monto <= 0) {
    errorPago.value = "El monto debe ser mayor a cero";
    return;
  }
  if (monto > restante.value + 0.01) {
    errorPago.value = `El monto excede lo que falta (${formatear(restante.value)})`;
    return;
  }
  if (medio.tipo === "fiado" && pos.idCliente === null) {
    errorPago.value = "La venta a fiado requiere un cliente identificado";
    return;
  }
  if (medio.tipo === "fiado" && Math.abs(monto - restante.value) > 0.01) {
    errorPago.value = "El fiado debe cubrir exactamente lo que falta";
    return;
  }

  let recibido: number | undefined;
  if (medio.tipo === "efectivo") {
    recibido = Number(recibidoEfectivo.value ?? monto);
    if (!Number.isFinite(recibido) || recibido < monto) {
      errorPago.value = "El efectivo recibido es menor al monto";
      return;
    }
  }

  pagos.value.push({ id_medio_pago: medio.id_medio_pago, nombre: medio.nombre, tipo: medio.tipo, monto, monto_recibido: recibido });
  errorPago.value = "";
  montoPago.value = restante.value > 0 ? restante.value : null;
  recibidoEfectivo.value = null;
}

function quitarPago(indice: number) {
  pagos.value.splice(indice, 1);
}

async function confirmarCobro() {
  if (!puedeCobrar.value || cobrando.value) return;
  cobrando.value = true;
  errorPago.value = "";
  const instantanea = JSON.parse(JSON.stringify(pos.carrito)) as typeof pos.carrito;
  const totalVenta = total.value;
  const cambioVenta = cambio.value;

  try {
    const resultado = await pos.cobrar(pagos.value);
    if (!resultado.ok) {
      errorPago.value = resultado.mensaje ?? "No se pudo registrar la venta";
      return;
    }
    showPago.value = false;
    ventaFinal.value = {
      uuid: resultado.uuid,
      total: totalVenta,
      cambio: cambioVenta,
      offline: resultado.offline,
      mensaje: resultado.mensaje,
    };

    if (resultado.offline) {
      imprimirTiqueteLocal({
        negocio: "TuSisTiendas",
        uuid: resultado.uuid,
        fecha: new Date().toLocaleString("es-CO"),
        items: instantanea.map((item) => ({
          nombre: item.nombre,
          cantidad: item.cantidad,
          precio: item.precio_unitario,
          subtotal: (item.precio_unitario - item.descuento) * item.cantidad,
        })),
        total: totalVenta,
        pagos: pagos.value.map((pago) => ({ metodo: pago.nombre, monto: pago.monto })),
        pendienteSincronizar: true,
      });
    } else {
      await imprimirDesdeServidor(resultado.uuid);
    }
  } finally {
    cobrando.value = false;
    pagos.value = [];
  }
}

async function imprimirDesdeServidor(uuid: string) {
  try {
    const venta = await api.get(`/ventas/por-uuid/${uuid}`);
    const tiquete = await api.get(`/ventas/${venta.data.id_venta}/tiquete`);
    imprimirTiquete(tiquete.data);
  } catch {
    // Si no hay tiquete disponible no se interrumpe el flujo de caja.
  }
}

async function reimprimir() {
  if (!ventaFinal.value) return;
  if (ventaFinal.value.offline) return;
  await imprimirDesdeServidor(ventaFinal.value.uuid);
}

function cerrarVentaFinal() {
  ventaFinal.value = null;
  nuevaVenta();
}

async function buscarClientes() {
  if (!busquedaCliente.value.trim()) return;
  buscandoCliente.value = true;
  try {
    const respuesta = await api.get("/clientes/buscar", { params: { q: busquedaCliente.value } });
    clientes.value = respuesta.data;
  } catch {
    clientes.value = [];
  } finally {
    buscandoCliente.value = false;
  }
}

function usarCliente(cliente: { id_cliente: number; nombre: string }) {
  pos.seleccionarCliente(cliente.id_cliente, cliente.nombre);
  showCliente.value = false;
  busquedaCliente.value = "";
  clientes.value = [];
}

function quitarCliente() {
  pos.seleccionarCliente(null, null);
}

onMounted(async () => {
  await pos.iniciar();
  enfocar();
});
</script>

<template>
  <div class="pos">
    <header class="barra">
      <button class="secundario" @click="router.push('/')">Volver</button>
      <div class="estado">
        <span class="etiqueta" :class="pos.online ? 'ok' : 'alerta'">
          {{ pos.online ? "En línea" : "Sin conexión" }}
        </span>
        <span v-if="pos.pendientes" class="etiqueta pendiente" :title="pos.ultimoError">
          {{ pos.pendientes }} por sincronizar
        </span>
        <span class="etiqueta" :class="pos.sesionCaja ? 'ok' : 'alerta'">
          {{ pos.sesionCaja ? "Caja abierta" : "Caja cerrada" }}
        </span>
      </div>
    </header>

    <div v-if="!pos.sesionCaja" class="aviso-caja">
      <strong>Caja cerrada.</strong> Abre la caja desde el módulo <strong>Caja</strong> para registrar ventas.
    </div>

    <div class="cuerpo">
      <section class="venta">
        <div class="escaneo">
          <input
            ref="scanRef"
            v-model="codigo"
            class="campo-escaneo"
            type="text"
            inputmode="numeric"
            autocomplete="off"
            placeholder="Escanee el código de barras"
            :disabled="!pos.sesionCaja"
            @keyup.enter="escanear"
          />
          <button class="primario" :disabled="!pos.sesionCaja" @click="escanear">Agregar</button>
        </div>
        <p v-if="mensajeEscaneo" class="aviso" :class="{ error: errorEscaneo }">{{ mensajeEscaneo }}</p>

        <div class="lineas">
          <p v-if="pos.carrito.length === 0" class="vacio">Escanee el primer producto para iniciar la venta</p>
          <div v-for="item in pos.carrito" :key="item.id_producto" class="linea">
            <div class="descripcion">
              <strong>{{ item.nombre }}</strong>
              <span class="muted">{{ formatear(item.precio_unitario) }} c/u</span>
            </div>
            <div class="cantidad">
              <button class="mini" @click="pos.cambiarCantidad(item.id_producto, item.cantidad - 1)">−</button>
              <span>{{ item.cantidad }}</span>
              <button class="mini" @click="pos.cambiarCantidad(item.id_producto, item.cantidad + 1)">+</button>
            </div>
            <div class="importe">{{ formatear((item.precio_unitario - item.descuento) * item.cantidad) }}</div>
            <button class="mini peligro" @click="pos.eliminarProducto(item.id_producto)">×</button>
          </div>
        </div>

        <div class="totales">
          <div class="fila"><span>Subtotal</span><span>{{ formatear(pos.totales.subtotal) }}</span></div>
          <div class="fila"><span>Impuestos</span><span>{{ formatear(pos.totales.impuestos) }}</span></div>
          <div class="fila total"><span>TOTAL</span><span>{{ formatear(total) }}</span></div>
        </div>
      </section>

      <aside class="panel">
        <div class="bloque">
          <h3>Cliente</h3>
          <button class="cliente" @click="showCliente = true">
            {{ pos.clienteNombre ?? "Consumidor final" }}
          </button>
          <button v-if="pos.idCliente" class="enlace" @click="quitarCliente">Quitar cliente</button>
        </div>

        <div class="bloque">
          <h3>Ventas temporales</h3>
          <p v-if="pos.temporales.length === 0" class="muted">No hay ventas guardadas</p>
          <div v-for="temporal in pos.temporales" :key="temporal.id" class="temporal">
            <div class="temporal-info">
              <span class="marca">Temporal</span>
              <strong>{{ temporal.nombre }}</strong>
              <span class="muted">{{ temporal.items.length }} producto(s)</span>
              <span v-if="temporal.descripcion" class="muted">Desc: {{ temporal.descripcion }}</span>
            </div>
            <div v-if="puedeEditarDescripcion(temporal)" class="temporal-desc">
              <input v-model="temporal.descripcion" placeholder="Descripción del porqué" />
              <button class="mini" @click="pos.actualizarTemporal(temporal.id, temporal.descripcion ?? null)">Guardar</button>
            </div>
            <div class="temporal-acciones">
              <button class="mini" @click="abrirTemporal(temporal.id)">Abrir</button>
              <button class="mini peligro" @click="temporalAEliminar = temporal.id">Eliminar</button>
            </div>
          </div>
        </div>

        <div class="acciones">
          <button class="primario grande" :disabled="pos.carrito.length === 0 || !pos.sesionCaja" @click="abrirModalPago">
            Cobrar {{ formatear(total) }}
          </button>
          <input v-model="descripcionTemporal" placeholder="Descripción del porqué (opcional)" />
          <button class="secundario" :disabled="pos.carrito.length === 0 || !pos.sesionCaja" @click="guardarTemporal">
            Guardar temporal
          </button>
          <button class="secundario" @click="nuevaVenta">Nueva venta</button>
        </div>
      </aside>
    </div>

    <!-- Cobro -->
    <div v-if="showPago" class="overlay" @click.self="showPago = false">
      <div class="modal">
        <h2>Cobrar {{ formatear(total) }}</h2>
        <p class="restante">Falta por cubrir: <strong>{{ formatear(restante) }}</strong></p>

        <div class="medios">
          <button
            v-for="medio in pos.medios"
            :key="medio.id_medio_pago"
            class="medio"
            :class="{ activo: medioSeleccionado?.id_medio_pago === medio.id_medio_pago }"
            @click="elegirMedio(medio)"
          >
            {{ medio.nombre }}
          </button>
        </div>

        <div class="captura">
          <label>
            Monto
            <input v-model.number="montoPago" type="number" min="0" />
          </label>
          <label v-if="medioSeleccionado?.tipo === 'efectivo'">
            Recibido
            <input v-model.number="recibidoEfectivo" type="number" min="0" placeholder="Efectivo entregado" />
          </label>
          <button class="secundario" @click="agregarPago">Agregar pago</button>
        </div>

        <ul v-if="pagos.length" class="lista-pagos">
          <li v-for="(pago, indice) in pagos" :key="indice">
            <span>{{ pago.nombre }}</span>
            <span>{{ formatear(pago.monto) }}</span>
            <button class="mini peligro" @click="quitarPago(indice)">×</button>
          </li>
        </ul>

        <p v-if="usaFiado" class="aviso">
          Fiado de {{ pos.clienteNombre ?? "sin cliente" }}: se descontará del saldo del cliente.
        </p>
        <p v-if="cambio > 0" class="cambio">Cambio: {{ formatear(cambio) }}</p>
        <p v-if="errorPago" class="aviso error">{{ errorPago }}</p>

        <div class="modal-acciones">
          <button class="secundario" @click="showPago = false">Cancelar</button>
          <button class="primario" :disabled="!puedeCobrar || cobrando" @click="confirmarCobro">
            {{ cobrando ? "Registrando…" : "Confirmar cobro" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Venta registrada -->
    <div v-if="ventaFinal" class="overlay">
      <div class="modal">
        <h2>Venta registrada</h2>
        <p class="restante">Total: <strong>{{ formatear(ventaFinal.total) }}</strong></p>
        <p v-if="ventaFinal.cambio > 0">Cambio: {{ formatear(ventaFinal.cambio) }}</p>
        <p v-if="ventaFinal.mensaje" class="aviso">{{ ventaFinal.mensaje }}</p>
        <p class="muted">Comprobante {{ ventaFinal.uuid.slice(0, 8) }}</p>
        <div class="modal-acciones">
          <button class="secundario" :disabled="ventaFinal.offline" @click="reimprimir">Reimprimir</button>
          <button class="primario" @click="cerrarVentaFinal">Nueva venta</button>
        </div>
      </div>
    </div>

    <!-- Cliente -->
    <div v-if="showCliente" class="overlay" @click.self="showCliente = false">
      <div class="modal">
        <h2>Buscar cliente</h2>
        <div class="escaneo">
          <input v-model="busquedaCliente" placeholder="Documento, nombre o teléfono" @keyup.enter="buscarClientes" />
          <button class="primario" @click="buscarClientes">Buscar</button>
        </div>
        <p v-if="buscandoCliente" class="muted">Buscando…</p>
        <ul class="lista-clientes">
          <li v-for="cliente in clientes" :key="cliente.id_cliente" @click="usarCliente(cliente)">
            <strong>{{ cliente.nombre }}</strong>
            <span class="muted">{{ cliente.numero_doc }}</span>
          </li>
        </ul>
        <div class="modal-acciones">
          <button class="secundario" @click="showCliente = false">Cerrar</button>
        </div>
      </div>
    </div>

    <!-- Confirmar eliminación de temporal -->
    <div v-if="temporalAEliminar" class="overlay" @click.self="temporalAEliminar = null">
      <div class="modal">
        <h2>Eliminar venta temporal</h2>
        <p>Esta venta no se ha cobrado. ¿Seguro que desea eliminarla?</p>
        <div class="modal-acciones">
          <button class="secundario" @click="temporalAEliminar = null">Conservar</button>
          <button class="primario peligro-fondo" @click="confirmarEliminarTemporal">Eliminar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pos { min-height: 100vh; display: flex; flex-direction: column; }
.barra { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.aviso-caja { margin: 16px 16px 0; padding: 12px 16px; border: 1px solid var(--warning); border-radius: 8px; background: rgba(243, 156, 18, 0.08); color: var(--warning); font-size: 14px; }
.estado { display: flex; gap: 8px; margin-left: auto; flex-wrap: wrap; }
.etiqueta { font-size: 12px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border); }
.etiqueta.ok { color: var(--success); border-color: var(--success); }
.etiqueta.alerta { color: var(--warning); border-color: var(--warning); }
.etiqueta.pendiente { color: var(--accent); border-color: var(--accent); }
.cuerpo { display: grid; grid-template-columns: 1fr 320px; gap: 16px; padding: 16px; flex: 1; }
.venta { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.escaneo { display: flex; gap: 8px; }
.campo-escaneo { font-size: 20px; padding: 16px; }
.lineas { flex: 1; overflow-y: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-card); }
.vacio { padding: 40px; text-align: center; color: var(--text-muted); }
.linea { display: grid; grid-template-columns: 1fr auto auto auto; gap: 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.descripcion { display: flex; flex-direction: column; }
.cantidad { display: flex; align-items: center; gap: 8px; font-size: 16px; }
.importe { font-weight: 700; min-width: 90px; text-align: right; }
.totales { border-top: 2px solid var(--border); padding-top: 12px; }
.fila { display: flex; justify-content: space-between; padding: 4px 0; }
.fila.total { font-size: 28px; font-weight: 800; color: var(--accent); }
.panel { display: flex; flex-direction: column; gap: 16px; }
.bloque h3 { margin-bottom: 8px; font-size: 14px; text-transform: uppercase; color: var(--text-muted); }
.cliente { width: 100%; text-align: left; background: var(--bg-card); border: 1px dashed var(--border); color: var(--text); padding: 12px; }
.enlace { background: none; color: var(--accent); padding: 4px 0; font-size: 12px; text-align: left; }
.temporal { display: flex; justify-content: space-between; gap: 8px; padding: 8px; border: 1px solid var(--warning); border-radius: 8px; margin-bottom: 8px; background: rgba(243, 156, 18, 0.08); }
.temporal-info { display: flex; flex-direction: column; gap: 2px; font-size: 13px; }
.marca { font-size: 10px; text-transform: uppercase; color: var(--warning); letter-spacing: 1px; }
.temporal-acciones { display: flex; flex-direction: column; gap: 4px; }
.acciones { margin-top: auto; display: flex; flex-direction: column; gap: 8px; }
.grande { padding: 18px; font-size: 20px; }
.secundario { background: var(--bg-card); border: 1px solid var(--border); color: var(--text); }
.mini { padding: 4px 10px; font-size: 14px; background: var(--bg-card); border: 1px solid var(--border); color: var(--text); }
.mini.peligro { color: var(--danger); border-color: var(--danger); }
.muted { color: var(--text-muted); font-size: 12px; }
.aviso { font-size: 13px; color: var(--warning); }
.aviso.error { color: var(--danger); }
.cambio { color: var(--success); font-weight: 700; }
.overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 16px; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 100%; max-width: 460px; display: flex; flex-direction: column; gap: 12px; max-height: 90vh; overflow-y: auto; }
.restante { color: var(--text-muted); }
.medios { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.medio { padding: 14px; background: var(--bg); border: 1px solid var(--border); color: var(--text); }
.medio.activo { border-color: var(--accent); background: rgba(233, 69, 96, 0.12); }
.captura { display: flex; flex-direction: column; gap: 8px; }
.captura label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--text-muted); }
.lista-pagos { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.lista-pagos li { display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: center; padding: 8px; border-bottom: 1px solid var(--border); }
.lista-clientes { list-style: none; max-height: 260px; overflow-y: auto; }
.lista-clientes li { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid var(--border); cursor: pointer; }
.lista-clientes li:hover { background: var(--primary-light); }
.modal-acciones { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.peligro-fondo { background: var(--danger); }
@media (max-width: 900px) {
  .cuerpo { grid-template-columns: 1fr; }
  .panel { order: -1; }
  .campo-escaneo { font-size: 16px; }
}
</style>
