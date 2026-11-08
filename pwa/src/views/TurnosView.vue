<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import api from "../api/client";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

type Vista = "mes" | "pintar" | "patrones" | "tarifas";

interface Turno {
  id_turno: number;
  id_usuario_titular: number;
  id_usuario_reemplazo: number | null;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  valor_total_turno: number;
  id_sucursal: number;
  estado_turno: string;
  hora_apertura_real?: string | null;
  hora_cierre_real?: string | null;
  nombre_titular?: string | null;
  nombre_reemplazo?: string | null;
  nombre_sucursal?: string | null;
}

interface Empleado {
  id_usuario: number;
  nombre_completo: string;
  rol: string;
  id_sucursal: number | null;
  activo?: boolean;
}

interface Sucursal {
  id_sucursal: number;
  nombre: string;
}

interface Festivo {
  id_festivo: number;
  fecha: string;
  nombre: string;
  recurrente_anual: boolean;
}

interface Tarifa {
  id_tarifa: number;
  nombre: string;
  hora_inicio: string;
  hora_fin: string;
  dias_semana: number[];
  valor: number;
  id_sucursal: number | null;
  nombre_sucursal?: string | null;
  prioridad: number;
  activa: boolean;
}

interface Plantilla {
  id_plantilla: number;
  nombre: string;
  dia_semana: number | null;
  dias_semana: number[];
  hora_inicio: string;
  hora_fin: string;
  valor_total_turno: number;
  usar_tarifa: boolean;
  id_usuario_titular: number;
  id_sucursal: number;
  activa: boolean;
  nombre_titular?: string | null;
  nombre_sucursal?: string | null;
}

interface GeneracionItem {
  fecha: string;
  id_usuario_titular: number;
  nombre_titular?: string | null;
  id_sucursal: number;
  nombre_sucursal?: string | null;
  hora_inicio: string;
  hora_fin: string;
  valor_total_turno: number;
  accion: string;
  motivo?: string | null;
  id_plantilla?: number | null;
  id_turno_existente?: number | null;
  es_festivo: boolean;
  horas_semana: number;
  advertencia_horas: boolean;
}

interface GeneracionRespuesta {
  dry_run: boolean;
  total_previstos: number;
  total_creados: number;
  total_existentes: number;
  total_conflictos: number;
  total_reemplazados: number;
  items: GeneracionItem[];
}

const DIAS = [
  { valor: 0, corto: "Lun", largo: "Lunes" },
  { valor: 1, corto: "Mar", largo: "Martes" },
  { valor: 2, corto: "Mié", largo: "Miércoles" },
  { valor: 3, corto: "Jue", largo: "Jueves" },
  { valor: 4, corto: "Vie", largo: "Viernes" },
  { valor: 5, corto: "Sáb", largo: "Sábado" },
  { valor: 6, corto: "Dom", largo: "Domingo" },
];

const esAdmin = computed(() => authStore.user?.rol === "administrador");
const vista = ref<Vista>("mes");
const mesActual = ref(startOfMonth(new Date()));
const pintarSemana = ref(startOfWeek(new Date()));

const turnosMes = ref<Turno[]>([]);
const festivosMes = ref<Festivo[]>([]);
const turnosPintar = ref<Turno[]>([]);
const festivosPintar = ref<Festivo[]>([]);
const empleados = ref<Empleado[]>([]);
const sucursales = ref<Sucursal[]>([]);
const tarifas = ref<Tarifa[]>([]);
const plantillas = ref<Plantilla[]>([]);

const loading = ref(false);
const loadingPintar = ref(false);
const saving = ref(false);
const generando = ref(false);

const toast = ref<{ tipo: "ok" | "error"; texto: string } | null>(null);
let toastTimer: number | undefined;

const diaDetalle = ref<string | null>(null);
const turnoDetalle = ref<Turno | null>(null);

const showTurnoForm = ref(false);
const turnoForm = ref({
  id_usuario_titular: 0,
  fecha: "",
  hora_inicio: "07:00",
  hora_fin: "15:00",
  id_sucursal: 0,
  usar_tarifa: true,
  valor_total_turno: 0,
});

const showPlantillaForm = ref(false);
const plantillaEditando = ref<Plantilla | null>(null);
const plantillaForm = ref({
  nombre: "",
  id_usuario_titular: 0,
  dias_semana: [0, 1, 2, 3, 4] as number[],
  hora_inicio: "07:00",
  hora_fin: "15:00",
  id_sucursal: 0,
  valor_total_turno: 0,
  usar_tarifa: true,
  activa: true,
});

const showTarifaForm = ref(false);
const tarifaEditando = ref<Tarifa | null>(null);
const tarifaForm = ref({
  nombre: "",
  hora_inicio: "08:00",
  hora_fin: "16:00",
  dias_semana: [0, 1, 2, 3, 4, 5, 6] as number[],
  valor: 0,
  id_sucursal: null as number | null,
  prioridad: 0,
  activa: true,
});

const showGenerar = ref(false);
const generacionPreview = ref<GeneracionRespuesta | null>(null);
const generacionForm = ref({
  fecha_desde: toISODate(startOfMonth(new Date())),
  fecha_hasta: toISODate(endOfMonth(new Date())),
  id_sucursal: null as number | null,
  id_usuarios: [] as number[],
  modo: "omitir" as "omitir" | "reemplazar",
});

const modoPincel = ref(true);
const pincel = ref({
  hora_inicio: "07:00",
  hora_fin: "15:00",
});
const mesFiltroSucursal = ref<number | null>(null);
const pincelFiltroSucursal = ref<number | null>(null);

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

function pad(valor: number): string {
  return String(valor).padStart(2, "0");
}

function toISODate(fecha: Date): string {
  return `${fecha.getFullYear()}-${pad(fecha.getMonth() + 1)}-${pad(fecha.getDate())}`;
}

function parseISO(valor: string): Date {
  const [year, month, day] = valor.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function startOfMonth(fecha: Date): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth(), 1);
}

function endOfMonth(fecha: Date): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth() + 1, 0);
}

function addMonths(fecha: Date, cantidad: number): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth() + cantidad, 1);
}

function addDays(fecha: Date, cantidad: number): Date {
  const resultado = new Date(fecha);
  resultado.setDate(resultado.getDate() + cantidad);
  return resultado;
}

function startOfWeek(fecha: Date): Date {
  const resultado = new Date(fecha);
  const dia = (resultado.getDay() + 6) % 7;
  resultado.setDate(resultado.getDate() - dia);
  resultado.setHours(0, 0, 0, 0);
  return resultado;
}

function monthLabel(fecha: Date): string {
  return fecha.toLocaleDateString("es-CO", { month: "long", year: "numeric" });
}

function rangoSemanaLabel(dias: Date[]): string {
  const opciones: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${dias[0].toLocaleDateString("es-CO", opciones)} – ${dias[6].toLocaleDateString("es-CO", opciones)}`;
}

function weekdayLong(fecha: Date): string {
  return fecha.toLocaleDateString("es-CO", { weekday: "long" });
}

function fechaParaDia(dia: number): string {
  const base = new Date();
  const actual = (base.getDay() + 6) % 7;
  return toISODate(addDays(base, (dia - actual + 7) % 7));
}

function esHoy(fecha: Date): boolean {
  return toISODate(fecha) === toISODate(new Date());
}

function money(valor: number | string | null | undefined): string {
  return "$" + Number(valor || 0).toLocaleString("es-CO");
}

function minutos(hora: string): number {
  const [h, m] = hora.split(":").map(Number);
  return h * 60 + m;
}

function duracionMin(hi: string, hf: string): number {
  const inicio = minutos(hi);
  const fin = minutos(hf);
  return fin <= inicio ? fin + 1440 - inicio : fin - inicio;
}

function hhmm(hora: string): string {
  return hora.slice(0, 5);
}

function rangoHorasTexto(hi: string, hf: string): string {
  return `${hhmm(hi)} – ${hhmm(hf)}`;
}

function rangoHoras(turno: Turno): string {
  return rangoHorasTexto(turno.hora_inicio, turno.hora_fin);
}

function estadoColor(estado: string): string {
  const colores: Record<string, string> = {
    programado: "#3b82f6",
    solicitud_reemplazo: "#f59e0b",
    reemplazo_pendiente_aprobacion: "#f97316",
    activo: "#22c55e",
    finalizado: "#8b5cf6",
    pagado: "#6366f1",
  };
  return colores[estado] || "#6b7280";
}

function estadoLabel(estado: string): string {
  return estado.replace(/_/g, " ");
}

function nombreEfectivo(turno: Turno): string {
  if (turno.id_usuario_reemplazo) {
    return `${turno.nombre_reemplazo || `#${turno.id_usuario_reemplazo}`} (reemplazo)`;
  }
  return turno.nombre_titular || `#${turno.id_usuario_titular}`;
}

function nombreSucursal(id: number | null | undefined): string {
  if (id === null || id === undefined) return "Todas";
  return sucursales.value.find((s) => s.id_sucursal === id)?.nombre || `Sucursal ${id}`;
}

function mensajeError(error: any): string {
  return (
    error?.response?.data?.error?.message ||
    error?.response?.data?.detail?.[0]?.msg ||
    error?.message ||
    "Ocurrió un error inesperado"
  );
}

function mostrarToast(tipo: "ok" | "error", texto: string): void {
  toast.value = { tipo, texto };
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.value = null;
  }, 4200);
}

// ---------------------------------------------------------------------------
// Tarifas: resolución local para mostrar el valor antes de guardar
// ---------------------------------------------------------------------------

function tarifaPara(
  fechaISO: string,
  hi: string,
  hf: string,
  idSucursal: number | null,
): Tarifa | null {
  if (!fechaISO || !hi || !hf) return null;
  const dia = (parseISO(fechaISO).getDay() + 6) % 7;
  const turnoIni = minutos(hi);
  const turnoFin = turnoIni + duracionMin(hi, hf);

  const candidatas = tarifas.value.filter((tarifa) => {
    if (!tarifa.activa || !tarifa.dias_semana.includes(dia)) return false;
    if (tarifa.id_sucursal !== null && tarifa.id_sucursal !== idSucursal) return false;
    const tarifaIni = minutos(tarifa.hora_inicio);
    const tarifaFin = tarifaIni + duracionMin(tarifa.hora_inicio, tarifa.hora_fin);
    return turnoIni >= tarifaIni && turnoFin <= tarifaFin;
  });

  candidatas.sort((a, b) => {
    const sucursalA = a.id_sucursal !== null ? 0 : 1;
    const sucursalB = b.id_sucursal !== null ? 0 : 1;
    return (
      sucursalA - sucursalB ||
      duracionMin(a.hora_inicio, a.hora_fin) - duracionMin(b.hora_inicio, b.hora_fin) ||
      b.prioridad - a.prioridad ||
      minutos(a.hora_inicio) - minutos(b.hora_inicio) ||
      a.id_tarifa - b.id_tarifa
    );
  });

  return candidatas[0] ?? null;
}

function valorTarifa(
  fechaISO: string,
  hi: string,
  hf: string,
  idSucursal: number | null,
): number | null {
  return tarifaPara(fechaISO, hi, hf, idSucursal)?.valor ?? null;
}

// ---------------------------------------------------------------------------
// Datos derivados del mes
// ---------------------------------------------------------------------------

const diasMes = computed(() => {
  const inicio = startOfWeek(startOfMonth(mesActual.value));
  const hoy = toISODate(new Date());
  return Array.from({ length: 42 }, (_, indice) => {
    const fecha = addDays(inicio, indice);
    return {
      fecha,
      iso: toISODate(fecha),
      dia: fecha.getDate(),
      delMes: fecha.getMonth() === mesActual.value.getMonth(),
      hoy: toISODate(fecha) === hoy,
    };
  });
});

const diasMesReales = computed(() => {
  const total = endOfMonth(mesActual.value).getDate();
  const hoy = toISODate(new Date());
  return Array.from({ length: total }, (_, indice) => {
    const fecha = new Date(mesActual.value.getFullYear(), mesActual.value.getMonth(), indice + 1);
    return {
      fecha,
      iso: toISODate(fecha),
      dia: indice + 1,
      hoy: toISODate(fecha) === hoy,
    };
  });
});

const turnosPorFecha = computed(() => {
  const mapa = new Map<string, Turno[]>();
  for (const turno of turnosMes.value) {
    const lista = mapa.get(turno.fecha) || [];
    lista.push(turno);
    mapa.set(turno.fecha, lista);
  }
  for (const lista of mapa.values()) {
    lista.sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  }
  return mapa;
});

const turnosMesActual = computed(() => {
  const prefijo = `${mesActual.value.getFullYear()}-${pad(mesActual.value.getMonth() + 1)}`;
  return turnosMes.value.filter((turno) => turno.fecha.startsWith(prefijo));
});

const totalMes = computed(() => turnosMesActual.value.length);
const empleadosConTurnos = computed(
  () => new Set(turnosMesActual.value.map((turno) => turno.id_usuario_titular)).size,
);

const diasPintar = computed(() =>
  Array.from({ length: 7 }, (_, indice) => addDays(pintarSemana.value, indice)),
);

const empleadosPintar = computed(() =>
  empleados.value.filter(
    (empleado) =>
      !pincelFiltroSucursal.value || empleado.id_sucursal === pincelFiltroSucursal.value,
  ),
);

const pincelValor = computed(() => {
  const fecha = toISODate(diasPintar.value[0]);
  return valorTarifa(
    fecha,
    pincel.value.hora_inicio,
    pincel.value.hora_fin,
    pincelFiltroSucursal.value ?? empleadosPintar.value[0]?.id_sucursal ?? null,
  );
});

const turnoFormValorSugerido = computed(() =>
  valorTarifa(
    turnoForm.value.fecha,
    turnoForm.value.hora_inicio,
    turnoForm.value.hora_fin,
    turnoForm.value.id_sucursal || null,
  ),
);

const plantillaValorSugerido = computed(() => {
  const dia = plantillaForm.value.dias_semana[0] ?? 0;
  return valorTarifa(
    fechaParaDia(dia),
    plantillaForm.value.hora_inicio,
    plantillaForm.value.hora_fin,
    plantillaForm.value.id_sucursal || null,
  );
});

const turnosDiaDetalle = computed(() =>
  diaDetalle.value ? turnosDia(diaDetalle.value) : [],
);

const diaDetalleFecha = computed(() =>
  diaDetalle.value ? parseISO(diaDetalle.value) : new Date(),
);
const diaDetalleIso = computed(() => diaDetalle.value || "");

const navLabel = computed(() =>
  vista.value === "pintar" ? rangoSemanaLabel(diasPintar.value) : monthLabel(mesActual.value),
);

const subtitulo = computed(() => {
  if (vista.value === "mes") {
    const n = empleadosConTurnos.value;
    const suc = mesFiltroSucursal.value
      ? ` · ${nombreSucursal(mesFiltroSucursal.value)}`
      : "";
    return `${totalMes.value} turnos · ${n} ${n === 1 ? "empleado" : "empleados"} con agenda${suc}`;
  }
  if (vista.value === "pintar") {
    const n = empleadosPintar.value.length;
    return `${n} ${n === 1 ? "empleado" : "empleados"} · ${rangoSemanaLabel(diasPintar.value)}`;
  }
  if (vista.value === "patrones") {
    const n = plantillas.value.filter((p) => p.activa).length;
    return `${n} ${n === 1 ? "patrón activo" : "patrones activos"}`;
  }
  const n = tarifas.value.filter((t) => t.activa).length;
  return `${n} ${n === 1 ? "regla de pago activa" : "reglas de pago activas"}`;
});

const generacionVisibles = computed(
  () => generacionPreview.value?.items.slice(0, 150) ?? [],
);
const generacionConflictos = computed(
  () => generacionPreview.value?.items.filter((item) => item.accion === "conflicto").length ?? 0,
);
const generacionAdvertencias = computed(
  () => generacionPreview.value?.items.filter((item) => item.advertencia_horas).length ?? 0,
);

function turnosDia(iso: string): Turno[] {
  return turnosPorFecha.value.get(iso) || [];
}

function visiblesDia(iso: string): Turno[] {
  return turnosDia(iso).slice(0, 3);
}

function restoDia(iso: string): number {
  return Math.max(0, turnosDia(iso).length - 3);
}

function esFestivo(iso: string): boolean {
  return festivosMes.value.some(
    (festivo) =>
      festivo.fecha === iso ||
      (festivo.recurrente_anual && festivo.fecha.slice(5) === iso.slice(5)),
  );
}

function nombreFestivo(iso: string): string {
  const festivo = [...festivosMes.value, ...festivosPintar.value].find(
    (item) =>
      item.fecha === iso ||
      (item.recurrente_anual && item.fecha.slice(5) === iso.slice(5)),
  );
  return festivo?.nombre || "Festivo";
}

function esFestivoPintar(fecha: Date): boolean {
  const iso = toISODate(fecha);
  return festivosPintar.value.some(
    (festivo) =>
      festivo.fecha === iso ||
      (festivo.recurrente_anual && festivo.fecha.slice(5) === iso.slice(5)),
  );
}

function turnosEmpleadoDia(idUsuario: number, iso: string): Turno[] {
  return turnosPintar.value.filter(
    (turno) =>
      turno.fecha === iso &&
      (turno.id_usuario_titular === idUsuario || turno.id_usuario_reemplazo === idUsuario),
  );
}

// ---------------------------------------------------------------------------
// Carga de datos
// ---------------------------------------------------------------------------

async function fetchMes(): Promise<void> {
  loading.value = true;
  try {
    const inicio = startOfWeek(startOfMonth(mesActual.value));
    const fin = addDays(inicio, 41);
    const params: Record<string, any> = {
      fecha_desde: toISODate(inicio),
      fecha_hasta: toISODate(fin),
    };
    if (mesFiltroSucursal.value) params.id_sucursal = mesFiltroSucursal.value;
    const response = await api.get("/turnos/calendario", { params });
    turnosMes.value = response.data.turnos || [];
    festivosMes.value = response.data.festivos || [];
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    loading.value = false;
  }
}

async function fetchPintar(): Promise<void> {
  if (!esAdmin.value) return;
  loadingPintar.value = true;
  try {
    const params: Record<string, any> = {
      fecha_desde: toISODate(diasPintar.value[0]),
      fecha_hasta: toISODate(diasPintar.value[6]),
    };
    if (pincelFiltroSucursal.value) params.id_sucursal = pincelFiltroSucursal.value;
    const response = await api.get("/turnos/calendario", { params });
    turnosPintar.value = response.data.turnos || [];
    festivosPintar.value = response.data.festivos || [];
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    loadingPintar.value = false;
  }
}

async function fetchEmpleados(): Promise<void> {
  try {
    const response = await api.get("/usuarios/", {
      params: { rol: "empleado", page_size: 100 },
    });
    empleados.value = response.data.items || [];
  } catch {
    // Silencioso: el calendario puede funcionar sin el listado.
  }
}

async function fetchSucursales(): Promise<void> {
  try {
    const response = await api.get("/turnos/sucursales");
    sucursales.value = response.data || [];
  } catch {
    // Silencioso.
  }
}

async function fetchTarifas(): Promise<void> {
  try {
    const response = await api.get("/turnos/tarifas");
    tarifas.value = response.data || [];
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function fetchPlantillas(): Promise<void> {
  try {
    const response = await api.get("/turnos/plantillas");
    plantillas.value = response.data || [];
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

// ---------------------------------------------------------------------------
// Navegación
// ---------------------------------------------------------------------------

function moverMes(cantidad: number): void {
  mesActual.value = addMonths(mesActual.value, cantidad);
}

function irHoyMes(): void {
  mesActual.value = startOfMonth(new Date());
}

function moverSemanaPintar(cantidad: number): void {
  pintarSemana.value = addDays(pintarSemana.value, cantidad * 7);
}

function navPrev(): void {
  if (vista.value === "pintar") moverSemanaPintar(-1);
  else moverMes(-1);
}

function navNext(): void {
  if (vista.value === "pintar") moverSemanaPintar(1);
  else moverMes(1);
}

function navHoy(): void {
  if (vista.value === "pintar") pintarSemana.value = startOfWeek(new Date());
  else irHoyMes();
}

// ---------------------------------------------------------------------------
// Detalle y acciones sobre turnos
// ---------------------------------------------------------------------------

function abrirDia(iso: string): void {
  diaDetalle.value = iso;
}

function abrirTurno(turno: Turno): void {
  diaDetalle.value = null;
  turnoDetalle.value = turno;
}

function abrirNuevoTurno(iso?: string, idUsuario?: number): void {
  const empleado =
    empleados.value.find((item) => item.id_usuario === idUsuario) || empleados.value[0];
  turnoForm.value = {
    id_usuario_titular: empleado?.id_usuario || 0,
    fecha: iso || toISODate(new Date()),
    hora_inicio: "07:00",
    hora_fin: "15:00",
    id_sucursal:
      empleado?.id_sucursal ||
      authStore.user?.id_sucursal ||
      sucursales.value[0]?.id_sucursal ||
      0,
    usar_tarifa: true,
    valor_total_turno: 0,
  };
  showTurnoForm.value = true;
}

function alCambiarEmpleadoTurno(): void {
  const empleado = empleados.value.find(
    (item) => item.id_usuario === turnoForm.value.id_usuario_titular,
  );
  if (empleado?.id_sucursal) {
    turnoForm.value.id_sucursal = empleado.id_sucursal;
  }
}

async function guardarTurno(): Promise<void> {
  if (!turnoForm.value.id_usuario_titular || !turnoForm.value.fecha) {
    mostrarToast("error", "Selecciona un empleado y una fecha");
    return;
  }
  if (turnoForm.value.usar_tarifa && turnoFormValorSugerido.value === null) {
    mostrarToast(
      "error",
      "No hay tarifa configurada para ese horario. Ajusta las horas o desactiva el cálculo automático.",
    );
    return;
  }
  saving.value = true;
  try {
    await api.post("/turnos/", {
      id_usuario_titular: turnoForm.value.id_usuario_titular,
      fecha: turnoForm.value.fecha,
      hora_inicio: turnoForm.value.hora_inicio,
      hora_fin: turnoForm.value.hora_fin,
      id_sucursal: turnoForm.value.id_sucursal || null,
      usar_tarifa: turnoForm.value.usar_tarifa,
      valor_total_turno: turnoForm.value.usar_tarifa
        ? null
        : turnoForm.value.valor_total_turno,
    });
    showTurnoForm.value = false;
    mostrarToast("ok", "Turno creado");
    await Promise.all([fetchMes(), fetchPintar()]);
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    saving.value = false;
  }
}

async function eliminarTurno(turno: Turno): Promise<void> {
  if (!confirm(`¿Eliminar el turno de ${nombreEfectivo(turno)}?`)) return;
  try {
    await api.delete(`/turnos/${turno.id_turno}`);
    turnoDetalle.value = null;
    mostrarToast("ok", "Turno eliminado");
    await Promise.all([fetchMes(), fetchPintar()]);
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function solicitarReemplazo(turno: Turno): Promise<void> {
  try {
    await api.post("/turnos/solicitud-reemplazo", { id_turno: turno.id_turno });
    turnoDetalle.value = null;
    mostrarToast("ok", "Solicitud de reemplazo enviada");
    await fetchMes();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function marcarPagoRecibido(turno: Turno): Promise<void> {
  try {
    const response = await api.get("/pagos/mis-pagos");
    const pago = (response.data || []).find((item: any) =>
      (item.detalles || []).some((detalle: any) => detalle.id_turno === turno.id_turno),
    );
    if (!pago) {
      mostrarToast("error", "No se encontró el pago asociado a este turno");
      return;
    }
    await api.patch(`/pagos/${pago.id_pago}/marcar-recibido`);
    mostrarToast("ok", "Pago marcado como recibido");
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

// ---------------------------------------------------------------------------
// Pintado por empleado
// ---------------------------------------------------------------------------

function pintarCelda(empleado: Empleado, fecha: Date): void {
  const iso = toISODate(fecha);
  const existentes = turnosEmpleadoDia(empleado.id_usuario, iso);
  if (existentes.length) {
    abrirTurno(existentes[0]);
    return;
  }
  if (!modoPincel.value) {
    abrirNuevoTurno(iso, empleado.id_usuario);
    return;
  }
  void crearTurnoRapido(empleado, iso);
}

async function crearTurnoRapido(empleado: Empleado, iso: string): Promise<void> {
  const sucursalTurno = empleado.id_sucursal || pincelFiltroSucursal.value || null;
  const valorDia = valorTarifa(
    iso,
    pincel.value.hora_inicio,
    pincel.value.hora_fin,
    sucursalTurno,
  );
  if (valorDia === null) {
    mostrarToast(
      "error",
      "No hay tarifa configurada para el horario del pincel. Ajusta las horas o crea una tarifa.",
    );
    return;
  }
  saving.value = true;
  try {
    await api.post("/turnos/", {
      id_usuario_titular: empleado.id_usuario,
      fecha: iso,
      hora_inicio: pincel.value.hora_inicio,
      hora_fin: pincel.value.hora_fin,
      id_sucursal: sucursalTurno,
      usar_tarifa: true,
      valor_total_turno: null,
    });
    mostrarToast("ok", `${empleado.nombre_completo}: turno creado`);
    await Promise.all([fetchPintar(), fetchMes()]);
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    saving.value = false;
  }
}

async function aplicarGeneracionSemana(idsUsuarios: number[]): Promise<void> {
  try {
    const response = await api.post("/turnos/generar", {
      fecha_desde: toISODate(diasPintar.value[0]),
      fecha_hasta: toISODate(diasPintar.value[6]),
      id_usuarios: idsUsuarios.length ? idsUsuarios : null,
      id_sucursal: pincelFiltroSucursal.value || null,
      modo: "omitir",
      dry_run: false,
      recalcular_tarifa: true,
    });
    const data: GeneracionRespuesta = response.data;
    mostrarToast(
      "ok",
      `Creados: ${data.total_creados} · existentes: ${data.total_existentes} · conflictos: ${data.total_conflictos}`,
    );
    await Promise.all([fetchPintar(), fetchMes()]);
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function aplicarPatronEmpleado(empleado: Empleado): Promise<void> {
  if (!confirm(`¿Aplicar el patrón semanal de ${empleado.nombre_completo} a la semana mostrada?`)) {
    return;
  }
  await aplicarGeneracionSemana([empleado.id_usuario]);
}

async function aplicarPatronesSemana(): Promise<void> {
  if (!confirm("¿Aplicar todos los patrones activos a la semana mostrada?")) return;
  await aplicarGeneracionSemana([]);
}

// ---------------------------------------------------------------------------
// Patrones semanales
// ---------------------------------------------------------------------------

function abrirNuevaPlantilla(): void {
  plantillaEditando.value = null;
  plantillaForm.value = {
    nombre: "",
    id_usuario_titular: empleados.value[0]?.id_usuario || 0,
    dias_semana: [0, 1, 2, 3, 4],
    hora_inicio: "07:00",
    hora_fin: "15:00",
    id_sucursal:
      authStore.user?.id_sucursal || sucursales.value[0]?.id_sucursal || 0,
    valor_total_turno: 0,
    usar_tarifa: true,
    activa: true,
  };
  showPlantillaForm.value = true;
}

function editarPlantilla(plantilla: Plantilla): void {
  plantillaEditando.value = plantilla;
  plantillaForm.value = {
    nombre: plantilla.nombre,
    id_usuario_titular: plantilla.id_usuario_titular,
    dias_semana: [...plantilla.dias_semana],
    hora_inicio: hhmm(plantilla.hora_inicio),
    hora_fin: hhmm(plantilla.hora_fin),
    id_sucursal: plantilla.id_sucursal,
    valor_total_turno: Number(plantilla.valor_total_turno),
    usar_tarifa: plantilla.usar_tarifa,
    activa: plantilla.activa,
  };
  showPlantillaForm.value = true;
}

async function guardarPlantilla(): Promise<void> {
  if (
    !plantillaForm.value.nombre.trim() ||
    !plantillaForm.value.id_usuario_titular ||
    !plantillaForm.value.dias_semana.length
  ) {
    mostrarToast("error", "Completa el nombre, el empleado y al menos un día");
    return;
  }
  if (!plantillaForm.value.id_sucursal) {
    mostrarToast("error", "Selecciona una sucursal");
    return;
  }
  if (plantillaForm.value.usar_tarifa && plantillaValorSugerido.value === null) {
    mostrarToast(
      "error",
      "No hay tarifa configurada para ese horario. Ajusta las horas o desactiva el cálculo automático.",
    );
    return;
  }
  saving.value = true;
  const payload: any = { ...plantillaForm.value };
  if (plantillaForm.value.usar_tarifa) {
    delete payload.valor_total_turno;
  }
  try {
    if (plantillaEditando.value) {
      await api.patch(`/turnos/plantillas/${plantillaEditando.value.id_plantilla}`, payload);
      mostrarToast("ok", "Patrón actualizado");
    } else {
      await api.post("/turnos/plantillas", {
        ...payload,
        valor_total_turno: plantillaForm.value.usar_tarifa
          ? null
          : plantillaForm.value.valor_total_turno,
      });
      mostrarToast("ok", "Patrón creado");
    }
    showPlantillaForm.value = false;
    await fetchPlantillas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    saving.value = false;
  }
}

async function togglePlantilla(plantilla: Plantilla): Promise<void> {
  try {
    await api.patch(`/turnos/plantillas/${plantilla.id_plantilla}`, {
      activa: !plantilla.activa,
    });
    await fetchPlantillas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function eliminarPlantilla(plantilla: Plantilla): Promise<void> {
  if (!confirm(`¿Desactivar el patrón "${plantilla.nombre}"?`)) return;
  try {
    await api.delete(`/turnos/plantillas/${plantilla.id_plantilla}`);
    mostrarToast("ok", "Patrón desactivado");
    await fetchPlantillas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

// ---------------------------------------------------------------------------
// Tarifas
// ---------------------------------------------------------------------------

function abrirNuevaTarifa(): void {
  tarifaEditando.value = null;
  tarifaForm.value = {
    nombre: "",
    hora_inicio: "08:00",
    hora_fin: "16:00",
    dias_semana: [0, 1, 2, 3, 4, 5, 6],
    valor: 0,
    id_sucursal: null,
    prioridad: 0,
    activa: true,
  };
  showTarifaForm.value = true;
}

function editarTarifa(tarifa: Tarifa): void {
  tarifaEditando.value = tarifa;
  tarifaForm.value = {
    nombre: tarifa.nombre,
    hora_inicio: hhmm(tarifa.hora_inicio),
    hora_fin: hhmm(tarifa.hora_fin),
    dias_semana: [...tarifa.dias_semana],
    valor: Number(tarifa.valor),
    id_sucursal: tarifa.id_sucursal,
    prioridad: tarifa.prioridad,
    activa: tarifa.activa,
  };
  showTarifaForm.value = true;
}

async function guardarTarifa(): Promise<void> {
  if (!tarifaForm.value.nombre.trim() || !tarifaForm.value.dias_semana.length) {
    mostrarToast("error", "Completa el nombre y al menos un día");
    return;
  }
  saving.value = true;
  try {
    if (tarifaEditando.value) {
      await api.patch(`/turnos/tarifas/${tarifaEditando.value.id_tarifa}`, tarifaForm.value);
      mostrarToast("ok", "Tarifa actualizada");
    } else {
      await api.post("/turnos/tarifas", tarifaForm.value);
      mostrarToast("ok", "Tarifa creada");
    }
    showTarifaForm.value = false;
    await fetchTarifas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    saving.value = false;
  }
}

async function toggleTarifa(tarifa: Tarifa): Promise<void> {
  try {
    await api.patch(`/turnos/tarifas/${tarifa.id_tarifa}`, { activa: !tarifa.activa });
    await fetchTarifas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

async function eliminarTarifa(tarifa: Tarifa): Promise<void> {
  if (!confirm(`¿Desactivar la tarifa "${tarifa.nombre}"?`)) return;
  try {
    await api.delete(`/turnos/tarifas/${tarifa.id_tarifa}`);
    mostrarToast("ok", "Tarifa desactivada");
    await fetchTarifas();
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  }
}

// ---------------------------------------------------------------------------
// Generación masiva
// ---------------------------------------------------------------------------

function abrirGenerar(): void {
  generacionPreview.value = null;
  generacionForm.value = {
    fecha_desde: toISODate(startOfMonth(mesActual.value)),
    fecha_hasta: toISODate(endOfMonth(mesActual.value)),
    id_sucursal: pincelFiltroSucursal.value,
    id_usuarios: [],
    modo: "omitir",
  };
  showGenerar.value = true;
}

async function previsualizarGeneracion(): Promise<void> {
  generando.value = true;
  try {
    const response = await api.post("/turnos/generar", {
      ...generacionForm.value,
      id_usuarios: generacionForm.value.id_usuarios.length
        ? generacionForm.value.id_usuarios
        : null,
      id_sucursal: generacionForm.value.id_sucursal || null,
      dry_run: true,
      recalcular_tarifa: true,
    });
    generacionPreview.value = response.data;
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    generando.value = false;
  }
}

async function confirmarGeneracion(): Promise<void> {
  if (!generacionPreview.value) {
    await previsualizarGeneracion();
    return;
  }
  const total =
    generacionPreview.value.total_creados + generacionPreview.value.total_reemplazados;
  if (!total) {
    mostrarToast("error", "No hay turnos nuevos por crear con esta configuración");
    return;
  }
  if (
    !confirm(
      `Se crearán ${total} turnos entre ${generacionForm.value.fecha_desde} y ${generacionForm.value.fecha_hasta}. ¿Continuar?`,
    )
  ) {
    return;
  }
  generando.value = true;
  try {
    const response = await api.post("/turnos/generar", {
      ...generacionForm.value,
      id_usuarios: generacionForm.value.id_usuarios.length
        ? generacionForm.value.id_usuarios
        : null,
      id_sucursal: generacionForm.value.id_sucursal || null,
      dry_run: false,
      recalcular_tarifa: true,
    });
    generacionPreview.value = response.data;
    mostrarToast(
      "ok",
      `Turnos creados: ${response.data.total_creados} · reemplazados: ${response.data.total_reemplazados}`,
    );
    await Promise.all([fetchMes(), fetchPintar(), fetchPlantillas()]);
  } catch (error: any) {
    mostrarToast("error", mensajeError(error));
  } finally {
    generando.value = false;
  }
}

// ---------------------------------------------------------------------------
// Ciclo de vida
// ---------------------------------------------------------------------------

watch(mesActual, () => {
  void fetchMes();
});

watch(mesFiltroSucursal, () => {
  void fetchMes();
});

watch(pintarSemana, () => {
  if (esAdmin.value) void fetchPintar();
});

watch(vista, (nueva) => {
  if (!esAdmin.value) return;
  if (nueva === "pintar") void fetchPintar();
  else if (nueva === "patrones") void fetchPlantillas();
  else if (nueva === "tarifas") void fetchTarifas();
});

onMounted(async () => {
  await fetchSucursales();
  if (esAdmin.value) {
    await Promise.all([fetchEmpleados(), fetchTarifas(), fetchPlantillas()]);
    const sucursalBase =
      authStore.user?.id_sucursal || sucursales.value[0]?.id_sucursal || null;
    turnoForm.value.id_sucursal = sucursalBase || 0;
    plantillaForm.value.id_sucursal = sucursalBase || 0;
    mesFiltroSucursal.value = sucursalBase;
    await fetchPintar();
  } else {
    mesFiltroSucursal.value = authStore.user?.id_sucursal || null;
  }
  await fetchMes();
});
</script>

<template>
  <div class="page turnos-page">
    <header class="page-header">
      <div class="title-block">
        <router-link to="/" class="btn-back">← Inicio</router-link>
        <h1>Turnos</h1>
        <p class="subtitle">{{ subtitulo }}</p>
      </div>
      <div v-if="esAdmin" class="header-actions">
        <button class="btn-secondary" @click="abrirGenerar">Generar mes</button>
        <button class="btn-primary" @click="abrirNuevoTurno()">+ Turno</button>
      </div>
    </header>

    <nav v-if="esAdmin" class="view-tabs">
      <button :class="{ active: vista === 'mes' }" @click="vista = 'mes'">Mes</button>
      <button :class="{ active: vista === 'pintar' }" @click="vista = 'pintar'">Pintar</button>
      <button :class="{ active: vista === 'patrones' }" @click="vista = 'patrones'">Patrones</button>
      <button :class="{ active: vista === 'tarifas' }" @click="vista = 'tarifas'">Tarifas</button>
    </nav>

    <div v-if="vista === 'mes' || vista === 'pintar'" class="period-bar">
      <button class="nav-arrow" aria-label="Anterior" @click="navPrev">‹</button>
      <button class="today-btn" @click="navHoy">Hoy</button>
      <h2 class="period-label">{{ navLabel }}</h2>
      <button class="nav-arrow" aria-label="Siguiente" @click="navNext">›</button>
    </div>

    <div v-if="toast" class="toast" :class="toast.tipo">{{ toast.texto }}</div>

  <section v-if="vista === 'mes'" class="month-section">
    <div v-if="loading" class="loading-pill">Cargando...</div>

    <div class="branch-bar">
      <label>Sucursal:</label>
      <select v-if="esAdmin" v-model="mesFiltroSucursal">
        <option :value="0">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id_sucursal" :value="s.id_sucursal">
          {{ s.nombre }}
        </option>
      </select>
      <span v-else class="branch-label">
        {{ mesFiltroSucursal ? nombreSucursal(mesFiltroSucursal) : 'Mi sucursal' }}
      </span>
    </div>

    <div class="month-desktop">
      <div class="month-head">
        <div v-for="dia in DIAS" :key="dia.valor" class="dow">{{ dia.corto }}</div>
      </div>
      <div class="month-grid">
        <div
          v-for="celda in diasMes"
          :key="celda.iso"
          class="day-cell"
          :class="{ outside: !celda.delMes, today: celda.hoy, holiday: esFestivo(celda.iso) }"
          :title="esFestivo(celda.iso) ? nombreFestivo(celda.iso) : ''"
          @click="abrirDia(celda.iso)"
        >
          <div class="day-top">
            <span class="day-num">{{ celda.dia }}</span>
            <span class="day-tags">
              <span v-if="esFestivo(celda.iso)" class="tag holiday-tag">Festivo</span>
              <button
                v-if="turnosDia(celda.iso).length"
                class="tag count-tag"
                :title="`Ver los ${turnosDia(celda.iso).length} turnos`"
                @click.stop="abrirDia(celda.iso)"
              >
                {{ turnosDia(celda.iso).length }}
              </button>
            </span>
          </div>
          <div class="day-list">
            <div
              v-for="turno in visiblesDia(celda.iso)"
              :key="turno.id_turno"
              class="mini-turno"
              @click.stop="abrirTurno(turno)"
            >
              <span class="mini-dot" :style="{ backgroundColor: estadoColor(turno.estado_turno) }"></span>
              <span class="mini-time">{{ rangoHoras(turno) }}</span>
              <span class="mini-name">{{ nombreEfectivo(turno) }}</span>
            </div>
            <button v-if="restoDia(celda.iso)" class="more-btn" @click.stop="abrirDia(celda.iso)">
              +{{ restoDia(celda.iso) }} más
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="agenda-mobile">
      <div
        v-for="celda in diasMesReales"
        :key="celda.iso"
        class="agenda-day"
        :class="{ holiday: esFestivo(celda.iso) }"
        @click="abrirDia(celda.iso)"
      >
        <div class="agenda-date">
          <span class="agenda-weekday">{{ weekdayLong(celda.fecha) }}</span>
          <span class="agenda-num" :class="{ today: celda.hoy }">{{ celda.dia }}</span>
          <span v-if="esFestivo(celda.iso)" class="agenda-holiday">Festivo</span>
        </div>
        <div class="agenda-body">
          <div v-if="!turnosDia(celda.iso).length" class="agenda-empty">Sin turnos</div>
          <div
            v-for="turno in visiblesDia(celda.iso)"
            :key="turno.id_turno"
            class="agenda-item"
            @click.stop="abrirTurno(turno)"
          >
            <span class="mini-dot" :style="{ backgroundColor: estadoColor(turno.estado_turno) }"></span>
            <span class="agenda-time">{{ rangoHoras(turno) }}</span>
            <span class="agenda-name">{{ nombreEfectivo(turno) }}</span>
            <span class="agenda-sucursal">{{ turno.nombre_sucursal || nombreSucursal(turno.id_sucursal) }}</span>
          </div>
          <button v-if="restoDia(celda.iso)" class="more-btn" @click.stop="abrirDia(celda.iso)">
            Mostrar {{ restoDia(celda.iso) }} más
          </button>
        </div>
      </div>
    </div>
  </section>

  <section v-if="vista === 'pintar'" class="paint-section">
    <div class="paint-toolbar">
      <label class="switch-row">
        <input v-model="modoPincel" type="checkbox" />
        <span>Modo pincel</span>
      </label>
      <span class="hint">{{ modoPincel ? "Clic en un día vacío crea el turno" : "Clic abre el formulario" }}</span>
      <div class="tool-field">
        <label>Sucursal</label>
        <select v-model="pincelFiltroSucursal">
          <option :value="null">Todas</option>
          <option v-for="sucursal in sucursales" :key="sucursal.id_sucursal" :value="sucursal.id_sucursal">
            {{ sucursal.nombre }}
          </option>
        </select>
      </div>
      <div class="tool-field">
        <label>Horario del pincel</label>
        <div class="time-pair">
          <input v-model="pincel.hora_inicio" type="time" />
          <span>a</span>
          <input v-model="pincel.hora_fin" type="time" />
        </div>
      </div>
      <div class="tool-field">
        <label>Valor referencia</label>
        <strong class="ref-value">{{ pincelValor !== null ? money(pincelValor) : "Sin tarifa" }}</strong>
      </div>
      <button class="btn-secondary" @click="aplicarPatronesSemana">Aplicar todos los patrones</button>
    </div>

    <div v-if="loadingPintar" class="loading-pill">Cargando semana...</div>

    <div class="paint-scroll">
      <div class="paint-grid">
        <div class="paint-head">
          <div class="paint-employee-head">Empleado</div>
          <div
            v-for="dia in diasPintar"
            :key="dia.getTime()"
            class="paint-day-head"
            :class="{ today: esHoy(dia), holiday: esFestivoPintar(dia) }"
          >
            <span>{{ DIAS[(dia.getDay() + 6) % 7].corto }}</span>
            <strong>{{ dia.getDate() }}</strong>
          </div>
        </div>

        <div v-for="empleado in empleadosPintar" :key="empleado.id_usuario" class="paint-row">
          <div class="paint-employee">
            <div class="paint-employee-info">
              <strong>{{ empleado.nombre_completo }}</strong>
              <span>{{ nombreSucursal(empleado.id_sucursal) }}</span>
            </div>
            <button class="mini-action" @click="aplicarPatronEmpleado(empleado)">Patrón</button>
          </div>
          <div
            v-for="dia in diasPintar"
            :key="dia.getTime()"
            class="paint-cell"
            :class="{ today: esHoy(dia), holiday: esFestivoPintar(dia) }"
            @click="pintarCelda(empleado, dia)"
          >
            <div
              v-for="turno in turnosEmpleadoDia(empleado.id_usuario, toISODate(dia))"
              :key="turno.id_turno"
              class="paint-chip"
              :style="{ borderLeftColor: estadoColor(turno.estado_turno) }"
              @click.stop="abrirTurno(turno)"
            >
              <span>{{ rangoHoras(turno) }}</span>
              <small>{{ turno.nombre_sucursal || nombreSucursal(turno.id_sucursal) }}</small>
            </div>
            <span
              v-if="!turnosEmpleadoDia(empleado.id_usuario, toISODate(dia)).length"
              class="paint-plus"
            >+</span>
            <button
              class="paint-add"
              title="Agregar otro turno"
              @click.stop="abrirNuevoTurno(toISODate(dia), empleado.id_usuario)"
            >+</button>
          </div>
        </div>

        <div v-if="!empleadosPintar.length" class="empty-state">No hay empleados para esta sucursal.</div>
      </div>
    </div>
    <p class="paint-hint">
      Selecciona una sucursal para filtrar. El valor del turno se calcula automáticamente con la tarifa vigente.
    </p>
  </section>

  <section v-if="vista === 'patrones'" class="panel-section">
    <div class="panel-head">
      <div>
        <h2>Patrones semanales</h2>
        <p>Configura una vez los horarios habituales y genera meses completos con vista previa.</p>
      </div>
      <div class="panel-actions">
        <button class="btn-secondary" @click="abrirGenerar">Generar mes</button>
        <button class="btn-primary" @click="abrirNuevaPlantilla">+ Nuevo patrón</button>
      </div>
    </div>

    <div class="pattern-grid">
      <article
        v-for="plantilla in plantillas"
        :key="plantilla.id_plantilla"
        class="pattern-card"
        :class="{ inactive: !plantilla.activa }"
      >
        <div class="card-top">
          <div>
            <strong>{{ plantilla.nombre }}</strong>
            <span class="muted">{{ plantilla.nombre_titular }}</span>
          </div>
          <span class="status-chip" :class="{ on: plantilla.activa }">
            {{ plantilla.activa ? "Activo" : "Inactivo" }}
          </span>
        </div>
        <div class="day-chips">
          <span
            v-for="dia in DIAS"
            :key="dia.valor"
            class="day-chip"
            :class="{ on: plantilla.dias_semana.includes(dia.valor) }"
          >{{ dia.corto }}</span>
        </div>
        <div class="card-meta">
          <span>{{ rangoHorasTexto(plantilla.hora_inicio, plantilla.hora_fin) }}</span>
          <span>{{ plantilla.nombre_sucursal || nombreSucursal(plantilla.id_sucursal) }}</span>
          <strong>{{ money(plantilla.valor_total_turno) }}</strong>
        </div>
        <div class="card-actions">
          <button class="mini-action" @click="editarPlantilla(plantilla)">Editar</button>
          <button class="mini-action" @click="togglePlantilla(plantilla)">
            {{ plantilla.activa ? "Desactivar" : "Activar" }}
          </button>
          <button class="mini-action danger" @click="eliminarPlantilla(plantilla)">Eliminar</button>
        </div>
      </article>
      <div v-if="!plantillas.length" class="empty-state">
        Aún no hay patrones. Crea el primero para empezar.
      </div>
    </div>
  </section>

  <section v-if="vista === 'tarifas'" class="panel-section">
    <div class="panel-head">
      <div>
        <h2>Tarifas de pago</h2>
        <p>
          Define rangos de horario y días. Al crear un turno, el valor se aplica automáticamente.
          Los valores actuales son de prueba.
        </p>
      </div>
      <button class="btn-primary" @click="abrirNuevaTarifa">+ Nueva tarifa</button>
    </div>

    <div class="tariff-list">
      <article
        v-for="tarifa in tarifas"
        :key="tarifa.id_tarifa"
        class="tariff-card"
        :class="{ inactive: !tarifa.activa }"
      >
        <div class="tariff-main">
          <strong>{{ tarifa.nombre }}</strong>
          <div class="day-chips compact">
            <span
              v-for="dia in DIAS"
              :key="dia.valor"
              class="day-chip"
              :class="{ on: tarifa.dias_semana.includes(dia.valor) }"
            >{{ dia.corto }}</span>
          </div>
        </div>
        <div class="tariff-data">
          <span>Horario</span>
          <strong>{{ rangoHorasTexto(tarifa.hora_inicio, tarifa.hora_fin) }}</strong>
        </div>
        <div class="tariff-data">
          <span>Sucursal</span>
          <strong>{{ tarifa.nombre_sucursal || nombreSucursal(tarifa.id_sucursal) }}</strong>
        </div>
        <div class="tariff-data">
          <span>Prioridad</span>
          <strong>{{ tarifa.prioridad }}</strong>
        </div>
        <div class="tariff-data">
          <span>Valor</span>
          <strong class="money">{{ money(tarifa.valor) }}</strong>
        </div>
        <div class="card-actions">
          <button class="mini-action" @click="editarTarifa(tarifa)">Editar</button>
          <button class="mini-action" @click="toggleTarifa(tarifa)">
            {{ tarifa.activa ? "Desactivar" : "Activar" }}
          </button>
          <button class="mini-action danger" @click="eliminarTarifa(tarifa)">Eliminar</button>
        </div>
      </article>
      <div v-if="!tarifas.length" class="empty-state">No hay tarifas configuradas.</div>
    </div>
  </section>

  <div v-if="diaDetalle" class="modal-overlay" @click.self="diaDetalle = null">
    <div class="modal card wide">
      <header class="modal-head">
        <div>
          <h2>{{ weekdayLong(diaDetalleFecha) }} {{ diaDetalleFecha.getDate() }}</h2>
          <p class="muted">
            {{ monthLabel(diaDetalleFecha) }}
            <span v-if="esFestivo(diaDetalleIso)"> · {{ nombreFestivo(diaDetalleIso) }}</span>
          </p>
        </div>
        <button class="icon-btn" @click="diaDetalle = null">×</button>
      </header>

      <div v-if="!turnosDiaDetalle.length" class="empty-state">No hay turnos este día.</div>
      <div v-else class="day-detail-list">
        <div
          v-for="turno in turnosDiaDetalle"
          :key="turno.id_turno"
          class="day-detail-row"
          @click="abrirTurno(turno)"
        >
          <span class="mini-dot" :style="{ backgroundColor: estadoColor(turno.estado_turno) }"></span>
          <div class="grow">
            <strong>{{ nombreEfectivo(turno) }}</strong>
            <span class="muted">
              {{ rangoHoras(turno) }} · {{ turno.nombre_sucursal || nombreSucursal(turno.id_sucursal) }}
            </span>
          </div>
          <span class="estado-text" :style="{ color: estadoColor(turno.estado_turno) }">
            {{ estadoLabel(turno.estado_turno) }}
          </span>
        </div>
      </div>

      <footer class="modal-actions">
        <button v-if="esAdmin" class="btn-primary" @click="abrirNuevoTurno(diaDetalleIso)">
          + Turno este día
        </button>
        <button class="btn-secondary" @click="diaDetalle = null">Cerrar</button>
      </footer>
    </div>
  </div>

  <div v-if="turnoDetalle" class="modal-overlay" @click.self="turnoDetalle = null">
    <div class="modal card">
      <header class="modal-head">
        <div>
          <h2>Detalle del turno</h2>
          <p class="muted">{{ nombreEfectivo(turnoDetalle) }}</p>
        </div>
        <button class="icon-btn" @click="turnoDetalle = null">×</button>
      </header>

      <div class="detail-grid">
        <div class="detail-item"><span>Fecha</span><strong>{{ turnoDetalle.fecha }}</strong></div>
        <div class="detail-item"><span>Horario</span><strong>{{ rangoHoras(turnoDetalle) }}</strong></div>
        <div class="detail-item"><span>Valor</span><strong>{{ money(turnoDetalle.valor_total_turno) }}</strong></div>
        <div class="detail-item">
          <span>Estado</span>
          <strong :style="{ color: estadoColor(turnoDetalle.estado_turno) }">
            {{ estadoLabel(turnoDetalle.estado_turno) }}
          </strong>
        </div>
        <div class="detail-item">
          <span>Sucursal</span>
          <strong>{{ turnoDetalle.nombre_sucursal || nombreSucursal(turnoDetalle.id_sucursal) }}</strong>
        </div>
        <div v-if="turnoDetalle.id_usuario_reemplazo" class="detail-item">
          <span>Reemplazo</span>
          <strong>{{ turnoDetalle.nombre_reemplazo || `#${turnoDetalle.id_usuario_reemplazo}` }}</strong>
        </div>
        <div v-if="turnoDetalle.hora_apertura_real" class="detail-item">
          <span>Apertura real</span>
          <strong>{{ new Date(turnoDetalle.hora_apertura_real).toLocaleString("es-CO") }}</strong>
        </div>
        <div v-if="turnoDetalle.hora_cierre_real" class="detail-item">
          <span>Cierre real</span>
          <strong>{{ new Date(turnoDetalle.hora_cierre_real).toLocaleString("es-CO") }}</strong>
        </div>
      </div>

      <footer class="modal-actions wrap">
        <button
          v-if="turnoDetalle.estado_turno === 'programado' && turnoDetalle.id_usuario_titular === authStore.user?.id_usuario"
          class="btn-warning"
          @click="solicitarReemplazo(turnoDetalle)"
        >
          Solicitar reemplazo
        </button>
        <button
          v-if="turnoDetalle.estado_turno === 'pagado' && turnoDetalle.id_usuario_titular === authStore.user?.id_usuario"
          class="btn-secondary"
          @click="marcarPagoRecibido(turnoDetalle)"
        >
          Marcar pago recibido
        </button>
        <button v-if="esAdmin" class="btn-danger" @click="eliminarTurno(turnoDetalle)">Eliminar</button>
        <button class="btn-secondary" @click="turnoDetalle = null">Cerrar</button>
      </footer>
    </div>
  </div>

  <div v-if="showTurnoForm" class="modal-overlay" @click.self="showTurnoForm = false">
    <div class="modal card">
      <header class="modal-head">
        <div>
          <h2>Nuevo turno</h2>
          <p class="muted">El valor se calcula con la tarifa configurada.</p>
        </div>
        <button class="icon-btn" @click="showTurnoForm = false">×</button>
      </header>

      <div class="form-group">
        <label>Empleado</label>
        <select v-model.number="turnoForm.id_usuario_titular" @change="alCambiarEmpleadoTurno">
          <option :value="0" disabled>Seleccionar empleado</option>
          <option v-for="empleado in empleados" :key="empleado.id_usuario" :value="empleado.id_usuario">
            {{ empleado.nombre_completo }}
          </option>
        </select>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Fecha</label>
          <input v-model="turnoForm.fecha" type="date" />
        </div>
        <div class="form-group">
          <label>Sucursal</label>
          <select v-model.number="turnoForm.id_sucursal">
            <option v-for="sucursal in sucursales" :key="sucursal.id_sucursal" :value="sucursal.id_sucursal">
              {{ sucursal.nombre }}
            </option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Inicio</label>
          <input v-model="turnoForm.hora_inicio" type="time" />
        </div>
        <div class="form-group">
          <label>Fin</label>
          <input v-model="turnoForm.hora_fin" type="time" />
        </div>
      </div>

      <label class="switch-row">
        <input v-model="turnoForm.usar_tarifa" type="checkbox" />
        <span>Calcular valor según tarifa</span>
      </label>
      <div v-if="turnoForm.usar_tarifa" class="auto-box">
        Valor automático:
        <strong>{{ turnoFormValorSugerido !== null ? money(turnoFormValorSugerido) : "Sin tarifa configurada" }}</strong>
      </div>
      <div v-else class="form-group">
        <label>Valor manual</label>
        <input v-model.number="turnoForm.valor_total_turno" type="number" min="0" step="1000" />
      </div>

      <footer class="modal-actions">
        <button class="btn-secondary" @click="showTurnoForm = false">Cancelar</button>
        <button class="btn-primary" :disabled="saving" @click="guardarTurno">
          {{ saving ? "Guardando..." : "Crear turno" }}
        </button>
      </footer>
    </div>
  </div>

  <div v-if="showPlantillaForm" class="modal-overlay" @click.self="showPlantillaForm = false">
    <div class="modal card wide">
      <header class="modal-head">
        <div>
          <h2>{{ plantillaEditando ? "Editar patrón" : "Nuevo patrón" }}</h2>
          <p class="muted">Se repetirá cada semana en los días seleccionados.</p>
        </div>
        <button class="icon-btn" @click="showPlantillaForm = false">×</button>
      </header>

      <div class="form-row">
        <div class="form-group">
          <label>Nombre del patrón</label>
          <input v-model="plantillaForm.nombre" type="text" placeholder="Ej. Turno mañana" />
        </div>
        <div class="form-group">
          <label>Empleado</label>
          <select v-model.number="plantillaForm.id_usuario_titular">
            <option v-for="empleado in empleados" :key="empleado.id_usuario" :value="empleado.id_usuario">
              {{ empleado.nombre_completo }}
            </option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Días</label>
        <div class="day-picker">
          <label
            v-for="dia in DIAS"
            :key="dia.valor"
            class="day-check"
            :class="{ active: plantillaForm.dias_semana.includes(dia.valor) }"
          >
            <input v-model="plantillaForm.dias_semana" type="checkbox" :value="dia.valor" />
            {{ dia.corto }}
          </label>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Inicio</label>
          <input v-model="plantillaForm.hora_inicio" type="time" />
        </div>
        <div class="form-group">
          <label>Fin</label>
          <input v-model="plantillaForm.hora_fin" type="time" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Sucursal</label>
          <select v-model.number="plantillaForm.id_sucursal">
            <option v-for="sucursal in sucursales" :key="sucursal.id_sucursal" :value="sucursal.id_sucursal">
              {{ sucursal.nombre }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Estado</label>
          <label class="switch-row padded">
            <input v-model="plantillaForm.activa" type="checkbox" />
            <span>{{ plantillaForm.activa ? "Activo" : "Inactivo" }}</span>
          </label>
        </div>
      </div>

      <label class="switch-row">
        <input v-model="plantillaForm.usar_tarifa" type="checkbox" />
        <span>Calcular valor automáticamente con tarifas</span>
      </label>
      <div v-if="plantillaForm.usar_tarifa" class="auto-box">
        Valor sugerido:
        <strong>{{ plantillaValorSugerido !== null ? money(plantillaValorSugerido) : "Sin regla" }}</strong>
      </div>
      <div v-else class="form-group">
        <label>Valor manual</label>
        <input v-model.number="plantillaForm.valor_total_turno" type="number" min="0" step="1000" />
      </div>

      <footer class="modal-actions">
        <button class="btn-secondary" @click="showPlantillaForm = false">Cancelar</button>
        <button class="btn-primary" :disabled="saving" @click="guardarPlantilla">
          {{ saving ? "Guardando..." : "Guardar patrón" }}
        </button>
      </footer>
    </div>
  </div>

  <div v-if="showTarifaForm" class="modal-overlay" @click.self="showTarifaForm = false">
    <div class="modal card wide">
      <header class="modal-head">
        <div>
          <h2>{{ tarifaEditando ? "Editar tarifa" : "Nueva tarifa" }}</h2>
          <p class="muted">Se aplica al crear turnos cuyo horario quede dentro del rango.</p>
        </div>
        <button class="icon-btn" @click="showTarifaForm = false">×</button>
      </header>

      <div class="form-row">
        <div class="form-group">
          <label>Nombre</label>
          <input v-model="tarifaForm.nombre" type="text" placeholder="Ej. Turno mañana" />
        </div>
        <div class="form-group">
          <label>Prioridad</label>
          <input v-model.number="tarifaForm.prioridad" type="number" />
        </div>
      </div>

      <div class="form-group">
        <label>Días</label>
        <div class="day-picker">
          <label
            v-for="dia in DIAS"
            :key="dia.valor"
            class="day-check"
            :class="{ active: tarifaForm.dias_semana.includes(dia.valor) }"
          >
            <input v-model="tarifaForm.dias_semana" type="checkbox" :value="dia.valor" />
            {{ dia.corto }}
          </label>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Inicio</label>
          <input v-model="tarifaForm.hora_inicio" type="time" />
        </div>
        <div class="form-group">
          <label>Fin</label>
          <input v-model="tarifaForm.hora_fin" type="time" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Valor del turno</label>
          <input v-model.number="tarifaForm.valor" type="number" min="0" step="1000" />
        </div>
        <div class="form-group">
          <label>Sucursal</label>
          <select v-model="tarifaForm.id_sucursal">
            <option :value="null">Todas las sucursales</option>
            <option v-for="sucursal in sucursales" :key="sucursal.id_sucursal" :value="sucursal.id_sucursal">
              {{ sucursal.nombre }}
            </option>
          </select>
        </div>
      </div>

      <label class="switch-row">
        <input v-model="tarifaForm.activa" type="checkbox" />
        <span>Tarifa activa</span>
      </label>

      <footer class="modal-actions">
        <button class="btn-secondary" @click="showTarifaForm = false">Cancelar</button>
        <button class="btn-primary" :disabled="saving" @click="guardarTarifa">
          {{ saving ? "Guardando..." : "Guardar tarifa" }}
        </button>
      </footer>
    </div>
  </div>

  <div v-if="showGenerar" class="modal-overlay" @click.self="showGenerar = false">
    <div class="modal card wide generate-modal">
      <header class="modal-head">
        <div>
          <h2>Generar turnos</h2>
          <p class="muted">Vista previa antes de guardar. Los festivos también generan turno.</p>
        </div>
        <button class="icon-btn" @click="showGenerar = false">×</button>
      </header>

      <div class="form-row">
        <div class="form-group">
          <label>Desde</label>
          <input v-model="generacionForm.fecha_desde" type="date" />
        </div>
        <div class="form-group">
          <label>Hasta</label>
          <input v-model="generacionForm.fecha_hasta" type="date" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Sucursal</label>
          <select v-model="generacionForm.id_sucursal">
            <option :value="null">Todas</option>
            <option v-for="sucursal in sucursales" :key="sucursal.id_sucursal" :value="sucursal.id_sucursal">
              {{ sucursal.nombre }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Modo</label>
          <select v-model="generacionForm.modo">
            <option value="omitir">Crear solo los que faltan</option>
            <option value="reemplazar">Reemplazar programados que se crucen</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Empleados (opcional)</label>
        <div class="employee-picker">
          <label v-for="empleado in empleados" :key="empleado.id_usuario" class="check-row">
            <input v-model="generacionForm.id_usuarios" type="checkbox" :value="empleado.id_usuario" />
            {{ empleado.nombre_completo }}
          </label>
        </div>
        <p class="hint">Si no seleccionas ninguno se usan todos los patrones activos.</p>
      </div>

      <div v-if="generacionPreview" class="preview">
        <div class="preview-summary">
          <div><span>Previstos</span><strong>{{ generacionPreview.total_previstos }}</strong></div>
          <div><span>Nuevos</span><strong class="ok-text">{{ generacionPreview.total_creados }}</strong></div>
          <div><span>Existentes</span><strong>{{ generacionPreview.total_existentes }}</strong></div>
          <div><span>Reemplazos</span><strong>{{ generacionPreview.total_reemplazados }}</strong></div>
          <div>
            <span>Conflictos</span>
            <strong :class="{ 'danger-text': generacionConflictos }">{{ generacionPreview.total_conflictos }}</strong>
          </div>
        </div>

        <p v-if="generacionConflictos" class="warning-text">
          {{ generacionConflictos }} turnos se cruzan con otros y no se crearán.
        </p>
        <p v-if="generacionAdvertencias" class="warning-text">
          {{ generacionAdvertencias }} turnos dejarían al empleado por encima de 44 horas semanales.
        </p>

        <div class="preview-list">
          <div class="preview-row preview-head">
            <span>Fecha</span><span>Empleado</span><span>Horario</span><span>Valor</span><span>Acción</span>
          </div>
          <div
            v-for="(item, indice) in generacionVisibles"
            :key="`${item.fecha}-${item.id_usuario_titular}-${indice}`"
            class="preview-row"
            :class="item.accion"
          >
            <span>{{ item.fecha }}</span>
            <span>{{ item.nombre_titular }}</span>
            <span>{{ rangoHorasTexto(item.hora_inicio, item.hora_fin) }}</span>
            <span>{{ money(item.valor_total_turno) }}</span>
            <span class="preview-action">
              {{ item.accion }}
              <small v-if="item.motivo">{{ item.motivo }}</small>
            </span>
          </div>
        </div>
        <p v-if="generacionPreview.items.length > generacionVisibles.length" class="hint">
          Mostrando {{ generacionVisibles.length }} de {{ generacionPreview.items.length }} movimientos.
        </p>
      </div>

      <footer class="modal-actions wrap">
        <button class="btn-secondary" @click="showGenerar = false">Cerrar</button>
        <button class="btn-secondary" :disabled="generando" @click="previsualizarGeneracion">
          {{ generando ? "Calculando..." : "Vista previa" }}
        </button>
        <button
          class="btn-primary"
          :disabled="generando || !generacionPreview"
          @click="confirmarGeneracion"
        >
          {{ generando ? "Generando..." : "Generar turnos" }}
        </button>
      </footer>
    </div>
  </div>
  </div>
</template>

<style scoped src="./turnos.css"></style>
