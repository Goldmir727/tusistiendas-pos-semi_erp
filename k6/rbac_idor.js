// k6/rbac_idor.js
// Tests de seguridad: control de acceso por rol (RBAC) e IDOR entre usuarios/sucursales.
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/rbac_idor.js

import http from 'k6/http';
import { check } from 'k6';
import { API, IDS } from './lib/config.js';
import { loginAs, authHeaders } from './lib/auth.js';

export const options = {
  vus: 2,
  iterations: 10,
  thresholds: {
    'checks': ['rate==1'],
  },
};

export default function () {
  const adminToken = loginAs('admin');
  const empleadoToken = loginAs('empleado');
  const cajeroToken = loginAs('cajero');

  // --- RBAC: empleado no puede administrar turnos/tarifas/patrones ---
  const adminEndpoints = [
    { method: 'GET', url: `${API}/turnos/tarifas` },
    { method: 'GET', url: `${API}/turnos/plantillas` },
    { method: 'POST', url: `${API}/turnos/generar`, body: JSON.stringify({ fecha_desde: '2026-11-01', fecha_hasta: '2026-11-07', id_usuarios: [IDS.empleadoPropio], modo: 'omitir', dry_run: true }) },
    { method: 'GET', url: `${API}/turnos/sucursales` },
  ];

  for (const ep of adminEndpoints) {
    const res = http.request(ep.method, ep.url, ep.body || null, authHeaders(empleadoToken));
    check(res, {
      [`empleado -> ${ep.method} ${ep.url} no es 2xx`]: (r) => r.status >= 400 && r.status < 500,
      [`empleado -> ${ep.method} ${ep.url} no es 5xx`]: (r) => r.status < 500,
    });
  }

  // --- RBAC: cajero no puede administrar turnos ---
  for (const ep of adminEndpoints) {
    const res = http.request(ep.method, ep.url, ep.body || null, authHeaders(cajeroToken));
    check(res, {
      [`cajero -> ${ep.method} ${ep.url} no es 2xx`]: (r) => r.status >= 400 && r.status < 500,
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
        // Si devuelve turnos, ninguno debe pertenecer al otro empleado
        return turnos.every((t) => t.id_usuario_titular !== IDS.empleadoOtro);
      } catch (e) {
        return r.status < 500;
      }
    },
  });

  // --- IDOR: acceso cruzado de sucursal ---
  const sucRes = http.get(
    `${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-30&id_sucursal=${IDS.sucursalOtra}`,
    authHeaders(empleadoToken),
  );
  check(sucRes, {
    'empleado no filtra otra sucursal con datos ajenos': (r) => {
      if (r.status === 403 || r.status === 404) return true;
      try {
        const body = r.json();
        const turnos = body.turnos || [];
        return turnos.every((t) => t.id_sucursal === IDS.sucursalPropia || t.id_sucursal === null);
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
