<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import api from "../api/client";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

interface Turno {
  id_turno: number;
  id_usuario_titular: number;
  id_usuario_reemplazo: number | null;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  valor_total_turno: number;
  estado_turno: string;
  id_sucursal: number;
}

interface Usuario {
  id_usuario: number;
  nombre_completo: string;
  rol: string;
  id_sucursal: number | null;
}

const turnos = ref<Turno[]>([]);
const usuarios = ref<Usuario[]>([]);
const loading = ref(true);
const currentWeekStart = ref(getMonday(new Date()));
const showCreateModal = ref(false);
const showDetailModal = ref(false);
const selectedTurno = ref<Turno | null>(null);
const selectedSlot = ref<{ date: string; hour: number } | null>(null);
const creating = ref(false);
const calendarStart = ref(6);
const calendarEnd = ref(22);

const newTurno = ref({
  id_usuario_titular: 0,
  fecha: "",
  hora_inicio: "08:00",
  hora_fin: "12:00",
  valor_total_turno: 0,
  id_sucursal: 1,
});

const HOURS = computed(() => {
  const start = calendarStart.value;
  const end = calendarEnd.value;
  return Array.from({ length: end - start + 1 }, (_, i) => i + start);
});
const DAY_NAMES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

function getMonday(d: Date): Date {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  date.setHours(0, 0, 0, 0);
  return date;
}

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

function addDays(d: Date, days: number): Date {
  const result = new Date(d);
  result.setDate(result.getDate() + days);
  return result;
}

const weekDates = computed(() => {
  return Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart.value, i));
});

const weekRangeLabel = computed(() => {
  const start = weekDates.value[0];
  const end = weekDates.value[6];
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  return `${start.toLocaleDateString("es-CO", opts)} - ${end.toLocaleDateString("es-CO", opts)}`;
});

function prevWeek() {
  currentWeekStart.value = addDays(currentWeekStart.value, -7);
}

function nextWeek() {
  currentWeekStart.value = addDays(currentWeekStart.value, 7);
}

function goToday() {
  currentWeekStart.value = getMonday(new Date());
}

function isToday(d: Date): boolean {
  const today = new Date();
  return d.toDateString() === today.toDateString();
}

function parseTime(timeStr: string): number {
  const [h, m] = timeStr.split(":").map(Number);
  return h + m / 60;
}

function isOvernight(t: Turno): boolean {
  return parseTime(t.hora_fin) <= parseTime(t.hora_inicio);
}

function formatHourLabel(h: number): string {
  return `${h.toString().padStart(2, "0")}:00`;
}

function nextDay(date: Date): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + 1);
  return d;
}

function getTurnosForDayAndHour(date: Date, hour: number): Turno[] {
  const dateStr = formatDate(date);
  const nextDateStr = formatDate(nextDay(date));
  return turnos.value.filter((t) => {
    const start = parseTime(t.hora_inicio);
    const end = parseTime(t.hora_fin);
    if (isOvernight(t)) {
      if (t.fecha === dateStr && start <= hour) return true;
      if (t.fecha === nextDateStr && end > hour) return true;
      return false;
    }
    return t.fecha === dateStr && start <= hour && end > hour;
  });
}

function isSlotOccupied(date: Date, hour: number): boolean {
  return getTurnosForDayAndHour(date, hour).length > 0;
}

function getTurnosForDay(date: Date): Turno[] {
  const dateStr = formatDate(date);
  const prevDateStr = formatDate(addDays(date, -1));
  return turnos.value.filter((t) => {
    if (t.fecha === dateStr) return true;
    if (isOvernight(t) && t.fecha === prevDateStr) {
      const end = parseTime(t.hora_fin);
      if (end > calendarStart.value) return true;
    }
    return false;
  });
}

function getTurnoPosition(turno: Turno, date: Date): { top: number; height: number } | null {
  const dateStr = formatDate(date);
  const nextDateStr = formatDate(nextDay(date));
  const start = parseTime(turno.hora_inicio);
  const end = parseTime(turno.hora_fin);
  const calendarH = calendarStart.value;

  if (isOvernight(turno)) {
    if (turno.fecha === dateStr) {
      const top = (start - calendarH) * 60;
      const height = (24 - start) * 60;
      return { top, height: Math.max(height, 30) };
    }
    if (turno.fecha === nextDateStr && end > calendarH) {
      const top = (calendarH - calendarH) * 60;
      const height = (end - calendarH) * 60;
      return { top, height: Math.max(height, 30) };
    }
    return null;
  }

  if (turno.fecha !== dateStr) return null;
  const top = (start - calendarH) * 60;
  const height = (end - start) * 60;
  return { top, height: Math.max(height, 30) };
}

function getUsuarioName(id: number): string {
  const u = usuarios.value.find((u) => u.id_usuario === id);
  return u ? u.nombre_completo : `#${id}`;
}

function getEstadoColor(estado: string): string {
  const colors: Record<string, string> = {
    programado: "#3b82f6",
    solicitud_reemplazo: "#f59e0b",
    reemplazo_pendiente_aprobacion: "#f97316",
    activo: "#22c55e",
    finalizado: "#8b5cf6",
    pagado: "#6366f1",
  };
  return colors[estado] || "#6b7280";
}

function handleSlotClick(date: Date, hour: number) {
  if (isSlotOccupied(date, hour)) return;
  selectedSlot.value = { date: formatDate(date), hour };
  newTurno.value = {
    id_usuario_titular: authStore.user?.id_usuario || 0,
    fecha: formatDate(date),
    hora_inicio: `${hour.toString().padStart(2, "0")}:00`,
    hora_fin: `${(hour + 4).toString().padStart(2, "0")}:00`,
    valor_total_turno: 0,
    id_sucursal: authStore.user?.id_sucursal || 1,
  };
  showCreateModal.value = true;
}

function handleTurnoClick(turno: Turno) {
  selectedTurno.value = turno;
  showDetailModal.value = true;
}

async function createTurno() {
  if (!newTurno.value.id_usuario_titular || !newTurno.value.fecha) return;
  creating.value = true;
  try {
    await api.post("/turnos/", {
      id_usuario_titular: newTurno.value.id_usuario_titular,
      fecha: newTurno.value.fecha,
      hora_inicio: newTurno.value.hora_inicio,
      hora_fin: newTurno.value.hora_fin,
      valor_total_turno: newTurno.value.valor_total_turno,
      id_sucursal: newTurno.value.id_sucursal,
    });
    showCreateModal.value = false;
    await fetchTurnos();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al crear turno");
  } finally {
    creating.value = false;
  }
}

async function deleteTurno(id: number) {
  if (!confirm("Eliminar este turno?")) return;
  try {
    await api.delete(`/turnos/${id}`);
    showDetailModal.value = false;
    await fetchTurnos();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error al eliminar");
  }
}

async function solicitarReemplazo(idTurno: number) {
  try {
    await api.post("/turnos/solicitud-reemplazo", { id_turno: idTurno });
    alert("Solicitud enviada");
    showDetailModal.value = false;
    await fetchTurnos();
  } catch (e: any) {
    alert(e.response?.data?.error?.message || "Error");
  }
}

async function fetchTurnos() {
  loading.value = true;
  try {
    const desde = formatDate(weekDates.value[0]);
    const hasta = formatDate(weekDates.value[6]);
    const response = await api.get("/turnos/", {
      params: { fecha_desde: desde, fecha_hasta: hasta, page_size: 100 },
    });
    turnos.value = response.data.items;
  } catch {} finally {
    loading.value = false;
  }
}

async function fetchUsuarios() {
  try {
    const response = await api.get("/usuarios/", { params: { page_size: 100 } });
    usuarios.value = response.data.items;
  } catch {}
}

async function fetchConfig() {
  try {
    const response = await api.get("/configuracion/public");
    if (response.data["turnos.hora_inicio"]) {
      calendarStart.value = parseInt(response.data["turnos.hora_inicio"]);
    }
    if (response.data["turnos.hora_fin"]) {
      calendarEnd.value = parseInt(response.data["turnos.hora_fin"]);
    }
  } catch {}
}

watch(currentWeekStart, fetchTurnos);

onMounted(async () => {
  await Promise.all([fetchTurnos(), fetchUsuarios(), fetchConfig()]);
});
</script>

<template>
  <div class="turnos-page">
    <header class="page-header">
      <div class="header-left">
        <h1>Calendario de Turnos</h1>
        <button class="btn-today" @click="goToday">Hoy</button>
      </div>
      <div class="header-center">
        <button class="nav-btn" @click="prevWeek">&larr;</button>
        <span class="week-label">{{ weekRangeLabel }}</span>
        <button class="nav-btn" @click="nextWeek">&rarr;</button>
      </div>
      <div class="header-right">
        <router-link to="/" class="btn-back">Volver</router-link>
      </div>
    </header>

    <div v-if="loading && turnos.length === 0" class="loading">Cargando turnos...</div>

    <div class="calendar-container">
      <div class="calendar-grid">
        <div class="time-gutter">
          <div class="gutter-header"></div>
          <div v-for="hour in HOURS" :key="hour" class="hour-label">
            {{ formatHourLabel(hour) }}
          </div>
        </div>

        <div v-for="(date, dayIndex) in weekDates" :key="dayIndex" class="day-column">
          <div class="day-header" :class="{ today: isToday(date) }">
            <span class="day-name">{{ DAY_NAMES[dayIndex] }}</span>
            <span class="day-number" :class="{ today: isToday(date) }">{{ date.getDate() }}</span>
          </div>

          <div class="day-body">
            <div
              v-for="hour in HOURS"
              :key="hour"
              class="time-slot"
              :class="{ occupied: isSlotOccupied(date, hour) }"
              @click="handleSlotClick(date, hour)"
            ></div>

            <div
              v-for="turno in getTurnosForDay(date)"
              :key="turno.id_turno + '-' + formatDate(date)"
              class="turno-block"
              :style="{
                top: (getTurnoPosition(turno, date)?.top || 0) + 'px',
                height: (getTurnoPosition(turno, date)?.height || 40) + 'px',
                backgroundColor: getEstadoColor(turno.estado_turno),
              }"
              @click.stop="handleTurnoClick(turno)"
            >
              <div class="turno-block-content">
                <span class="turno-time">{{ turno.hora_inicio }} - {{ turno.hora_fin }}</span>
                <span class="turno-name">{{ getUsuarioName(turno.id_usuario_titular) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal card">
        <h2>Crear Turno</h2>
        <div class="form-group">
          <label>Empleado</label>
          <select v-model="newTurno.id_usuario_titular">
            <option :value="0" disabled>Seleccionar empleado</option>
            <option v-for="u in usuarios" :key="u.id_usuario" :value="u.id_usuario">
              {{ u.nombre_completo }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Fecha</label>
            <input v-model="newTurno.fecha" type="date" />
          </div>
          <div class="form-group">
            <label>Sucursal</label>
            <select v-model="newTurno.id_sucursal">
              <option :value="1">Sucursal 1</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Hora Inicio</label>
            <input v-model="newTurno.hora_inicio" type="time" />
          </div>
          <div class="form-group">
            <label>Hora Fin</label>
            <input v-model="newTurno.hora_fin" type="time" />
          </div>
        </div>
        <div class="form-group">
          <label>Valor Turno ($)</label>
          <input v-model.number="newTurno.valor_total_turno" type="number" min="0" step="1000" />
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateModal = false">Cancelar</button>
          <button class="primary" :disabled="creating || !newTurno.id_usuario_titular" @click="createTurno">
            {{ creating ? "Creando..." : "Crear Turno" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDetailModal && selectedTurno" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal card">
        <div class="modal-header">
          <h2>Detalle del Turno</h2>
          <button class="btn-close" @click="showDetailModal = false">&times;</button>
        </div>
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Empleado</span>
            <span class="detail-value">{{ getUsuarioName(selectedTurno.id_usuario_titular) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Fecha</span>
            <span class="detail-value">{{ selectedTurno.fecha }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Horario</span>
            <span class="detail-value">{{ selectedTurno.hora_inicio }} - {{ selectedTurno.hora_fin }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Valor</span>
            <span class="detail-value">${{ selectedTurno.valor_total_turno.toLocaleString() }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Estado</span>
            <span
              class="detail-value estado-badge"
              :style="{ backgroundColor: getEstadoColor(selectedTurno.estado_turno) }"
            >
              {{ selectedTurno.estado_turno.replace("_", " ") }}
            </span>
          </div>
          <div v-if="selectedTurno.id_usuario_reemplazo" class="detail-item">
            <span class="detail-label">Reemplazo</span>
            <span class="detail-value">{{ getUsuarioName(selectedTurno.id_usuario_reemplazo) }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button
            v-if="selectedTurno.estado_turno === 'programado'"
            class="btn-warning"
            @click="solicitarReemplazo(selectedTurno.id_turno)"
          >
            Solicitar Reemplazo
          </button>
          <button class="btn-danger" @click="deleteTurno(selectedTurno.id_turno)">Eliminar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.turnos-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 700;
}

.btn-today {
  background: var(--border);
  color: var(--text);
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 6px;
}

.btn-today:hover {
  background: var(--text-muted);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-btn {
  background: none;
  color: var(--text);
  font-size: 20px;
  padding: 4px 12px;
  border-radius: 6px;
}

.nav-btn:hover {
  background: var(--border);
}

.week-label {
  font-size: 16px;
  font-weight: 600;
  min-width: 200px;
  text-align: center;
}

.btn-back {
  color: var(--accent);
  text-decoration: none;
  font-size: 14px;
}

.loading {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
}

.calendar-container {
  flex: 1;
  overflow: auto;
  padding: 0 24px 24px;
}

.calendar-grid {
  display: flex;
  min-width: 100%;
  position: relative;
}

.time-gutter {
  width: 60px;
  flex-shrink: 0;
}

.gutter-header {
  height: 56px;
  border-bottom: 1px solid var(--border);
}

.hour-label {
  height: 60px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding-right: 8px;
  font-size: 11px;
  color: var(--text-muted);
  transform: translateY(-7px);
}

.day-column {
  flex: 1;
  min-width: 120px;
  border-left: 1px solid var(--border);
}

.day-header {
  height: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  position: sticky;
  top: 0;
  z-index: 2;
}

.day-header.today {
  background: rgba(233, 69, 96, 0.1);
}

.day-name {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.day-number {
  font-size: 20px;
  font-weight: 700;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.day-number.today {
  background: var(--accent);
  color: white;
}

.day-body {
  position: relative;
}

.time-slot {
  height: 60px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s;
}

.time-slot:hover {
  background: rgba(233, 69, 96, 0.05);
}

.time-slot.occupied {
  cursor: default;
}

.turno-block {
  position: absolute;
  left: 2px;
  right: 2px;
  border-radius: 6px;
  padding: 4px 6px;
  overflow: hidden;
  cursor: pointer;
  z-index: 1;
  transition: transform 0.15s, box-shadow 0.15s;
  display: flex;
  align-items: flex-start;
}

.turno-block:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 3;
}

.turno-block-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.turno-time {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.9;
  white-space: nowrap;
}

.turno-name {
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  width: 90%;
  max-width: 440px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  font-size: 18px;
  margin-bottom: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-close {
  background: none;
  color: var(--text-muted);
  font-size: 24px;
  padding: 0;
  line-height: 1;
}

.btn-close:hover {
  color: var(--text);
  background: none;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.detail-grid {
  display: grid;
  gap: 16px;
  margin-bottom: 24px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 15px;
  font-weight: 500;
}

.estado-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  text-transform: capitalize;
  width: fit-content;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-secondary {
  background: var(--border);
  color: var(--text);
}

.btn-secondary:hover {
  background: var(--text-muted);
}

.btn-warning {
  background: var(--warning);
  color: white;
}

.btn-warning:hover {
  opacity: 0.9;
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-danger:hover {
  opacity: 0.9;
}

.header-right {
  display: flex;
  align-items: center;
}
</style>
