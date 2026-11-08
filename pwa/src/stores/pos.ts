import { computed, ref } from "vue";
import { defineStore } from "pinia";
import api from "../api/client";
import { dbLocal } from "../lib/db";

export interface ItemCarrito {
  id_producto: number;
  nombre: string;
  codigo_barras: string | null;
  cantidad: number;
  precio_unitario: number;
  descuento: number;
  iva_porcentaje: number;
}

export interface VentaTemporal {
  id: string;
  nombre: string;
  items: ItemCarrito[];
  id_cliente: number | null;
  cliente_nombre: string | null;
  descripcion?: string | null;
  creado_en: string;
  actualizado_en: string;
  id_usuario_creador?: number;
}

export interface MedioPago {
  id_medio_pago: number;
  nombre: string;
  tipo: string;
  requiere_referencia?: boolean;
}

export interface PagoLinea {
  id_medio_pago: number;
  nombre: string;
  tipo: string;
  monto: number;
  monto_recibido?: number;
}

export interface SesionCaja {
  id_sesion_caja: number;
  id_punto_venta: number;
  id_usuario_abre_caja?: number | null;
  base_inicial: number;
  estado: string;
}

interface ProductoPOS {
  id_producto: number;
  nombre_producto: string;
  precio_venta: number;
  iva_porcentaje?: number;
  stock_actual?: number;
  codigos_barras?: { codigo_barras: string }[];
}

interface VentaEnCola {
  uuid: string;
  payload: Record<string, unknown>;
  creado_en: string;
}

// Sin tasa configurada el producto no causa IVA: no se inventa un 19 %.
const IVA_DEFECTO = 0;

function generarUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (caracter) => {
    const aleatorio = (Math.random() * 16) | 0;
    const valor = caracter === "x" ? aleatorio : (aleatorio & 0x3) | 0x8;
    return valor.toString(16);
  });
}

function ahora(): string {
  return new Date().toISOString();
}

export const usePOSStore = defineStore("pos", () => {
  const carrito = ref<ItemCarrito[]>([]);
  const temporales = ref<VentaTemporal[]>([]);
  const temporalActivo = ref<string | null>(null);
  const idCliente = ref<number | null>(null);
  const clienteNombre = ref<string | null>(null);
  const sesionCaja = ref<SesionCaja | null>(null);
  const medios = ref<MedioPago[]>([]);
  const online = ref(typeof navigator === "undefined" ? true : navigator.onLine);
  const pendientes = ref(0);
  const sincronizando = ref(false);
  const ultimoError = ref("");
  const idPuntoVenta = ref(Number(localStorage.getItem("punto_venta") || 1));

  const mapaCodigos = new Map<string, ProductoPOS>();
  const mapaProductos = new Map<number, ProductoPOS>();
  let temporizadorBorrador: number | undefined;

  const cantidadItems = computed(() => carrito.value.reduce((total, item) => total + item.cantidad, 0));

  const totales = computed(() => {
    let subtotal = 0;
    let impuestos = 0;
    let descuento = 0;
    for (const item of carrito.value) {
      const base = (item.precio_unitario - item.descuento) * item.cantidad;
      subtotal += base;
      impuestos += base * (item.iva_porcentaje / 100);
      descuento += item.descuento * item.cantidad;
    }
    return {
      subtotal: Math.round(subtotal),
      impuestos: Math.round(impuestos),
      descuento: Math.round(descuento),
      total: Math.round(subtotal + impuestos),
    };
  });

  function aplicarProducto(producto: ProductoPOS, codigo: string | null, cantidad = 1) {
    const existente = carrito.value.find((item) => item.id_producto === producto.id_producto);
    if (existente) {
      existente.cantidad += cantidad;
    } else {
      carrito.value.push({
        id_producto: producto.id_producto,
        nombre: producto.nombre_producto,
        codigo_barras: codigo ?? producto.codigos_barras?.[0]?.codigo_barras ?? null,
        cantidad,
        precio_unitario: Number(producto.precio_venta),
        descuento: 0,
        iva_porcentaje: Number(producto.iva_porcentaje ?? IVA_DEFECTO),
      });
    }
    programarBorrador();
  }

  function agregarProducto(producto: ProductoPOS, cantidad = 1) {
    aplicarProducto(producto, null, cantidad);
  }

  async function agregarPorCodigo(codigo: string): Promise<{ ok: boolean; motivo?: string }> {
    let producto = mapaCodigos.get(codigo) ?? null;

    if (!producto) {
      const guardado = await dbLocal.get<ProductoPOS>("codigos", codigo);
      if (guardado) {
        producto = mapaProductos.get(guardado.id_producto) ?? guardado;
      }
    }

    if (!producto && online.value) {
      try {
        const respuesta = await api.get(`/productos/buscar/${encodeURIComponent(codigo)}`);
        producto = respuesta.data as ProductoPOS;
        await guardarEnCatalogo(producto, codigo);
      } catch {
        producto = null;
      }
    }

    if (!producto) {
      return { ok: false, motivo: online.value ? "Producto no encontrado" : "Producto no está en el catálogo local" };
    }

    aplicarProducto(producto, codigo);
    return { ok: true };
  }

  function cambiarCantidad(id_producto: number, cantidad: number) {
    const item = carrito.value.find((linea) => linea.id_producto === id_producto);
    if (!item) return;
    if (cantidad <= 0) {
      eliminarProducto(id_producto);
      return;
    }
    item.cantidad = cantidad;
    programarBorrador();
  }

  function eliminarProducto(id_producto: number) {
    carrito.value = carrito.value.filter((item) => item.id_producto !== id_producto);
    programarBorrador();
  }

  function seleccionarCliente(id: number | null, nombre: string | null) {
    idCliente.value = id;
    clienteNombre.value = nombre;
    programarBorrador();
  }

  function programarBorrador() {
    window.clearTimeout(temporizadorBorrador);
    temporizadorBorrador = window.setTimeout(async () => {
      if (carrito.value.length > 0 || idCliente.value) {
        const borrador = JSON.parse(
          JSON.stringify({
            carrito: carrito.value,
            idCliente: idCliente.value,
            clienteNombre: clienteNombre.value,
            temporalActivo: temporalActivo.value,
          }),
        );
        await dbLocal.put("estado", borrador, "borrador");
      } else {
        await dbLocal.eliminar("estado", "borrador");
      }
    }, 150);
  }

  async function guardarEnCatalogo(producto: ProductoPOS, codigo?: string) {
    mapaProductos.set(producto.id_producto, producto);
    await dbLocal.put("productos", producto);
    const codigos = codigo ? [codigo] : (producto.codigos_barras ?? []).map((c) => c.codigo_barras);
    for (const valor of codigos) {
      mapaCodigos.set(valor, producto);
      await dbLocal.put("codigos", producto, valor);
    }
  }

  async function cargarCatalogo() {
    try {
      let pagina = 1;
      let paginas = 1;
      do {
        const respuesta = await api.get("/productos/", { params: { page: pagina, page_size: 100 } });
        for (const producto of respuesta.data.items as ProductoPOS[]) {
          await guardarEnCatalogo(producto);
        }
        paginas = respuesta.data.pages ?? 1;
        pagina += 1;
      } while (pagina <= paginas);
    } catch {
      // Sin conexión se usa el catálogo ya guardado en el dispositivo.
    }
  }

  async function hidratarCatalogo() {
    const productos = await dbLocal.getAll<ProductoPOS>("productos");
    for (const producto of productos) {
      mapaProductos.set(producto.id_producto, producto);
    }
    const temporalesLocales = await dbLocal.getAll<VentaTemporal>("temporales");
    temporales.value = temporalesLocales.sort((a, b) => (a.actualizado_en < b.actualizado_en ? 1 : -1));
    await actualizarPendientes();
  }

  async function cargarSesionCaja() {
    try {
      const respuesta = await api.get("/caja/abierta");
      sesionCaja.value = respuesta.data && respuesta.data.id_sesion_caja ? (respuesta.data as SesionCaja) : null;
      await cargarTemporalesBackend();
    } catch {
      sesionCaja.value = sesionCaja.value;
    }
  }

  async function cargarMedios() {
    try {
      const respuesta = await api.get("/ventas/medios");
      medios.value = respuesta.data as MedioPago[];
      try {
        // IndexedDB no puede clonar proxies reactivos: guardar una copia plana.
        await dbLocal.put("estado", JSON.parse(JSON.stringify(medios.value)), "medios");
      } catch {
        // Si falla la caché, conservar los medios cargados desde el backend.
      }
    } catch {
      const guardados = await dbLocal.get<MedioPago[]>("estado", "medios");
      medios.value = guardados ?? [];
    }
  }

  async function iniciar() {
    await hidratarCatalogo();

    const borrador = await dbLocal.get<{
      carrito: ItemCarrito[];
      idCliente: number | null;
      clienteNombre: string | null;
      temporalActivo: string | null;
    }>("estado", "borrador");
    if (borrador) {
      carrito.value = borrador.carrito ?? [];
      idCliente.value = borrador.idCliente ?? null;
      clienteNombre.value = borrador.clienteNombre ?? null;
      temporalActivo.value = borrador.temporalActivo ?? null;
    }

    await cargarMedios();
    await cargarSesionCaja();
    if (online.value) {
      await cargarCatalogo();
      await sincronizar();
    }

    window.addEventListener("online", manejarConexion);
    window.addEventListener("offline", manejarConexion);
  }

  function manejarConexion() {
    online.value = navigator.onLine;
    if (online.value) {
      void sincronizar();
      void cargarCatalogo();
      void cargarMedios();
    }
  }

  function mapTemporalBackend(data: any): VentaTemporal {
    return {
      id: String(data.id_venta_temporal),
      nombre: data.nombre,
      items: (data.items || []) as ItemCarrito[],
      id_cliente: data.id_cliente ?? null,
      cliente_nombre: data.cliente_nombre ?? null,
      descripcion: data.descripcion ?? null,
      creado_en: data.created_at,
      actualizado_en: data.updated_at,
      id_usuario_creador: data.id_usuario_creador,
    };
  }

  async function cargarTemporalesBackend() {
    if (!online.value || !sesionCaja.value) return;
    try {
      const resp = await api.get("/ventas-temporales/", {
        params: { id_sesion_caja: sesionCaja.value.id_sesion_caja },
      });
      temporales.value = (resp.data || [])
        .map(mapTemporalBackend)
        .sort((a: VentaTemporal, b: VentaTemporal) =>
          a.actualizado_en < b.actualizado_en ? 1 : -1
        );
    } catch {}
  }

  function nombreSugerido(): string {
    const hora = new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
    return `Venta ${hora}`;
  }

  async function guardarTemporal(nombre?: string, descripcion?: string | null): Promise<VentaTemporal | null> {
    if (carrito.value.length === 0) return null;

    const items = JSON.parse(JSON.stringify(carrito.value)) as ItemCarrito[];

    if (online.value && sesionCaja.value) {
      try {
        const resp = await api.post("/ventas-temporales/", {
          id_sesion_caja: sesionCaja.value.id_sesion_caja,
          nombre: nombre?.trim() || nombreSugerido(),
          id_cliente: idCliente.value,
          cliente_nombre: clienteNombre.value,
          items,
          descripcion: descripcion ?? null,
        });
        const temporal = mapTemporalBackend(resp.data);
        temporales.value = [temporal, ...temporales.value.filter((t) => t.id !== temporal.id)];
        await dbLocal.put("temporales", temporal);
        limpiarVenta();
        return temporal;
      } catch {
        // Fallback local si falla el backend.
      }
    }

    const temporal: VentaTemporal = {
      id: temporalActivo.value ?? generarUuid(),
      nombre: nombre?.trim() || nombreSugerido(),
      items,
      id_cliente: idCliente.value,
      cliente_nombre: clienteNombre.value,
      descripcion: descripcion ?? null,
      creado_en: ahora(),
      actualizado_en: ahora(),
    };

    await dbLocal.put("temporales", temporal);
    const existentes = await dbLocal.getAll<VentaTemporal>("temporales");
    temporales.value = existentes.sort((a, b) => (a.actualizado_en < b.actualizado_en ? 1 : -1));

    limpiarVenta();
    return temporal;
  }

  async function actualizarTemporal(id: string, descripcion: string | null) {
    if (online.value) {
      try {
        const resp = await api.patch(`/ventas-temporales/${id}`, { descripcion });
        const actualizado = mapTemporalBackend(resp.data);
        temporales.value = temporales.value.map((t) => (t.id === id ? actualizado : t));
        await dbLocal.put("temporales", actualizado);
      } catch (e: any) {
        alert(e.response?.data?.error?.message || "No se pudo actualizar la descripción");
      }
    } else {
      const temporal = temporales.value.find((t) => t.id === id);
      if (temporal) {
        temporal.descripcion = descripcion;
        temporal.actualizado_en = ahora();
        await dbLocal.put("temporales", JSON.parse(JSON.stringify(temporal)));
      }
    }
  }

  async function abrirTemporal(id: string) {
    const temporal = temporales.value.find((t) => t.id === id);
    if (!temporal) return;
    carrito.value = temporal.items;
    idCliente.value = temporal.id_cliente ?? null;
    clienteNombre.value = temporal.cliente_nombre ?? null;
    temporalActivo.value = temporal.id;
    temporales.value = temporales.value.filter((item) => item.id !== id);
    await dbLocal.eliminar("temporales", id);
    if (online.value) {
      try {
        await api.delete(`/ventas-temporales/${id}`);
      } catch {}
    }
    programarBorrador();
  }

  async function eliminarTemporal(id: string) {
    temporales.value = temporales.value.filter((item) => item.id !== id);
    await dbLocal.eliminar("temporales", id);
    if (temporalActivo.value === id) temporalActivo.value = null;
    if (online.value) {
      try {
        await api.delete(`/ventas-temporales/${id}`);
      } catch {}
    }
  }

  function limpiarVenta() {
    carrito.value = [];
    idCliente.value = null;
    clienteNombre.value = null;
    temporalActivo.value = null;
    void dbLocal.eliminar("estado", "borrador");
  }

  async function actualizarPendientes() {
    const cola = await dbLocal.getAll<VentaEnCola>("outbox");
    pendientes.value = cola.length;
    return cola;
  }

  function descontarStockLocal(items: ItemCarrito[]) {
    for (const item of items) {
      const producto = mapaProductos.get(item.id_producto);
      if (!producto) continue;
      producto.stock_actual = Math.max(0, Number(producto.stock_actual ?? 0) - item.cantidad);
    }
  }

  async function encolarVenta(payload: Record<string, unknown>, items: ItemCarrito[]) {
    await dbLocal.put("outbox", { uuid: String(payload.uuid), payload, creado_en: ahora() });
    descontarStockLocal(items);
    await actualizarPendientes();
  }

  async function cobrar(pagos: PagoLinea[]): Promise<{ ok: boolean; offline: boolean; uuid: string; mensaje?: string }> {
    if (carrito.value.length === 0) {
      return { ok: false, offline: false, uuid: "", mensaje: "La venta está vacía" };
    }
    if (pagos.length === 0) {
      return { ok: false, offline: false, uuid: "", mensaje: "Registre al menos un pago" };
    }

    const uuid = generarUuid();
    const items = JSON.parse(JSON.stringify(carrito.value)) as ItemCarrito[];
    const sesion = sesionCaja.value;

    if (!sesion) {
      return { ok: false, offline: false, uuid: "", mensaje: "Abra la caja antes de cobrar" };
    }

    const payload: Record<string, unknown> = {
      uuid,
      id_sesion_caja: sesion.id_sesion_caja,
      id_punto_venta: sesion.id_punto_venta ?? idPuntoVenta.value,
      id_cliente: idCliente.value,
      detalles: items.map((item) => ({
        id_producto: item.id_producto,
        cantidad: item.cantidad,
        precio_unitario: item.precio_unitario,
        descuento: item.descuento,
        iva_porcentaje: item.iva_porcentaje,
      })),
      pagos: pagos.map((pago) => ({
        id_medio_pago: pago.id_medio_pago,
        monto: pago.monto,
        monto_recibido: pago.monto_recibido,
      })),
      origen: online.value ? "online" : "offline",
      creado_offline_en: online.value ? null : ahora(),
    };

    if (!online.value) {
      await encolarVenta(payload, items);
      limpiarVenta();
      return {
        ok: true,
        offline: true,
        uuid,
        mensaje: "Venta guardada en el dispositivo. Se enviará al recuperar la conexión.",
      };
    }

    try {
      const respuesta = await api.post("/ventas/", payload);
      limpiarVenta();
      return { ok: true, offline: false, uuid: String(respuesta.data.uuid ?? uuid) };
    } catch (error: any) {
      if (!error?.response) {
        // Se cayó la red durante el cobro: la venta no se pierde, queda en cola.
        await encolarVenta(payload, items);
        limpiarVenta();
        return {
          ok: true,
          offline: true,
          uuid,
          mensaje: "Sin conexión: la venta quedó guardada y se sincronizará automáticamente.",
        };
      }
      ultimoError.value = error.response?.data?.error?.message ?? "Error al registrar la venta";
      return { ok: false, offline: false, uuid: "", mensaje: ultimoError.value };
    }
  }

  async function sincronizar() {
    if (sincronizando.value || !online.value) return;
    sincronizando.value = true;
    try {
      const cola = await actualizarPendientes();
      for (const venta of cola) {
        try {
          await api.post("/ventas/", venta.payload);
          await dbLocal.eliminar("outbox", venta.uuid);
        } catch (error: any) {
          if (error?.response?.status === 409) {
            // Ya existía en el servidor: idempotencia por UUID resuelta.
            await dbLocal.eliminar("outbox", venta.uuid);
            continue;
          }
          if (error?.response) {
            ultimoError.value = error.response?.data?.error?.message ?? "No se pudo sincronizar una venta";
            break;
          }
          break;
        }
      }
      await actualizarPendientes();
    } finally {
      sincronizando.value = false;
    }
  }

  function cambiarPuntoVenta(id: number) {
    idPuntoVenta.value = id;
    localStorage.setItem("punto_venta", String(id));
  }

  return {
    carrito,
    temporales,
    temporalActivo,
    idCliente,
    clienteNombre,
    sesionCaja,
    medios,
    online,
    pendientes,
    sincronizando,
    ultimoError,
    idPuntoVenta,
    cantidadItems,
    totales,
    iniciar,
    agregarProducto,
    agregarPorCodigo,
    cambiarCantidad,
    eliminarProducto,
    seleccionarCliente,
    guardarTemporal,
    actualizarTemporal,
    abrirTemporal,
    eliminarTemporal,
    limpiarVenta,
    cobrar,
    sincronizar,
    cargarMedios,
    cargarSesionCaja,
    cargarCatalogo,
    cambiarPuntoVenta,
  };
});
