// k6/rbac_idor.js
// Tests de seguridad: control de acceso por rol (RBAC) e IDOR entre usuarios/sucursales.
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/rbac_idor.js

import http from 'k6/http';
import { check } from 'k6';
import { API, IDS } from './lib/config.js';
import { login, authHeaders } from './lib/auth.js';
import { USERS } from './lib/config.js';

export const options = {
  vus: 2,
  iterations: 10,
  thresholds: {
    'checks': ['rate==1'],
  },
};

export function setup() {
  const admin = login(USERS.admin.email, USERS.admin.password);
  const empleado = login(USERS.empleado.email, USERS.empleado.password);
  const cajero = login(USERS.cajero.email, USERS.cajero.password);
  return {
    adminToken: admin.token,
    empleadoToken: empleado.token,
    cajeroToken: cajero.token,
  };
}

export default function (data) {
  const adminToken = data.adminToken;
  const empleadoToken = data.empleadoToken;
  const cajeroToken = data.cajeroToken;

  // --- RBAC: empleado no puede administrar turnos/tarifas/patrones ---
  const adminEndpoints = [
    { method: 'GET', url: `${API}/turnos/tarifas` },
    { method: 'GET', url: `${API}/turnos/plantillas` },
    { method: 'POST', url: `${API}/turnos/generar`, body: JSON.stringify({ fecha_desde: '2026-11-01', fecha_hasta: '2026-11-07', id_usuarios: [IDS.empleadoPropio], modo: 'omitir', dry_run: true }) },
  ];

  for (const ep of adminEndpoints) {
    const res = http.request(ep.method, ep.url, ep.body || null, authHeaders(empleadoToken));
    check(res, {
      [`empleado -> ${ep.method} ${ep.url} no es 2xx`]: (r) => r.status >= 400 && r.status < 500,
      [`empleado -> ${ep.method} ${ep.url} no es 5xx`]: (r) => r.status < 500,
    });
  }

  for (const ep of adminEndpoints) {
    const res = http.request(ep.method, ep.url, ep.body || null, authHeaders(cajeroToken));
    check(res, {
      [`cajero -> ${ep.method} ${ep.url} no es 2xx`]: (r) => r.status >= 400 && r.status < 500,
    });
  }

  // --- Lectura de sucursales: cualquier usuario autenticado ---
  for (const tok of [empleadoToken, cajeroToken, adminToken]) {
    const res = http.get(`${API}/turnos/sucursales`, authHeaders(tok));
    check(res, {
      'usuario autenticado puede listar sucursales': (r) => r.status === 200,
    });
  }

  // --- IDOR: empleado leyendo turnos de otro empleado ---
  const idorRes = http.get(
    `${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-30&id_usuario=${IDS.empleadoOtro}`,
    authHeaders(empleadoToken),
  );
  check(idorRes, {
    'empleado no ve turnos de otro (403/404 o vacío)': (r) => {
      if (r.status === 403 || r.status === 404) return true;
      try {
        const body = r.json();
        const turnos = body.turnos || [];
        return turnos.every((t) => t.id_usuario_titular !== IDS.empleadoOtro && t.id_usuario_reemplazo !== IDS.empleadoOtro);
      } catch (e) {
        return r.status < 500;
      }
    },
  });

  // --- IDOR: acceso cruzado de sucursal (no debe ver turnos de otros empleados) ---
  const sucRes = http.get(
    `${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-30&id_sucursal=${IDS.sucursalOtra}`,
    authHeaders(empleadoToken),
  );
  check(sucRes, {
    'empleado no ve turnos de otros empleados en otra sucursal': (r) => {
      if (r.status === 403 || r.status === 404) return true;
      try {
        const body = r.json();
        const turnos = body.turnos || [];
        // El empleado (id 6) puede tener turnos en sucursal 2 (reemplazos), pero nunca de otros empleados
        return turnos.every((t) => t.id_usuario_titular === IDS.empleadoPropio || t.id_usuario_reemplazo === IDS.empleadoPropio);
      } catch (e) {
        return r.status < 500;
      }
    },
  });

  // --- Sin token ---
  const noTokenRes = http.get(`${API}/turnos/tarifas`);
  check(noTokenRes, {
    'sin token -> 401': (r) => r.status === 401,
  });

  // --- Token inválido ---
  const badTokenRes = http.get(`${API}/turnos/tarifas`, {
    headers: { Authorization: 'Bearer totally.invalid.token' },
  });
  check(badTokenRes, {
    'token inválido -> 401': (r) => r.status === 401,
  });
}
