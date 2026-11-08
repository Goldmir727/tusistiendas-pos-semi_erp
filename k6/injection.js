// k6/injection.js
// Tests de seguridad: inyección SQL, XSS y path traversal en parámetros del API.
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/injection.js

import http from 'k6/http';
import { check } from 'k6';
import { API } from './lib/config.js';
import { loginAs, authHeaders } from './lib/auth.js';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    'checks': ['rate==1'],
  },
};

const SQLI = [
  "' OR 1=1 --",
  "'; DROP TABLE turnos_calendario; --",
  "1 UNION SELECT * FROM usuarios",
  "2026-11-01' OR '1'='1",
];

const XSS = [
  "<script>alert(1)</script>",
  '"><img src=x onerror=alert(1)>',
  "javascript:alert(1)",
];

export default function () {
  const token = loginAs('admin');
  const h = authHeaders(token);

  // --- SQLi en parámetros de fecha ---
  for (const payload of SQLI) {
    const res = http.get(
      `${API}/turnos/calendario?fecha_desde=${encodeURIComponent(payload)}&fecha_hasta=2026-11-07`,
      h,
    );
    check(res, {
      [`sqli fecha_desde "${payload.slice(0, 20)}" no es 5xx`]: (r) => r.status < 500,
      [`sqli fecha_desde "${payload.slice(0, 20)}" no filtra datos`]: (r) => !(r.body || '').includes('id_usuario'),
    });
  }

  // --- SQLi en id_usuario / id_sucursal ---
  for (const payload of ["1 OR 1=1", "1; SELECT 1", "' OR '1'='1"]) {
    const res = http.get(
      `${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-07&id_usuario=${encodeURIComponent(payload)}`,
      h,
    );
    check(res, {
      [`sqli id_usuario "${payload}" no es 5xx`]: (r) => r.status < 500,
    });
  }

  // --- Path traversal en IDs ---
  for (const payload of ['../', '..%2F', '%2e%2e%2f', '1/../../etc/passwd']) {
    const res = http.get(`${API}/turnos/${encodeURIComponent(payload)}`, h);
    check(res, {
      [`path traversal "${payload}" no es 5xx`]: (r) => r.status < 500,
      [`path traversal "${payload}" no expone archivos`]: (r) => !(r.body || '').includes('root:'),
    });
  }

  // --- XSS en payloads de creación de turno ---
  for (const payload of XSS) {
    const res = http.post(
      `${API}/turnos/`,
      JSON.stringify({
        id_usuario_titular: 6,
        fecha: '2026-11-10',
        hora_inicio: '07:00',
        hora_fin: '15:00',
        id_sucursal: 1,
        usar_tarifa: false,
        valor_total_turno: 54000,
        observacion: payload,
      }),
      h,
    );
    check(res, {
      [`xss en turno no es 5xx`]: (r) => r.status < 500,
      [`xss no se refleja sin escapar`]: (r) => !(r.body || '').includes('<script>'),
    });
  }

  // --- Payload sobredimensionado ---
  const big = 'A'.repeat(100000);
  const res = http.post(
    `${API}/turnos/`,
    JSON.stringify({
      id_usuario_titular: 6,
      fecha: '2026-11-10',
      hora_inicio: '07:00',
      hora_fin: '15:00',
      id_sucursal: 1,
      usar_tarifa: false,
      valor_total_turno: 54000,
      observacion: big,
    }),
    h,
  );
  check(res, {
    'payload grande no provoca 5xx/OOM': (r) => r.status < 500,
  });
}
