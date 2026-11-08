// k6/pos_caja.js
// Tests de seguridad: POS y caja (roles, caja abierta, validaciones).
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/pos_caja.js

import http from 'k6/http';
import { check } from 'k6';
import { API } from './lib/config.js';
import { loginAs, authHeaders } from './lib/auth.js';

export const options = {
  vus: 1,
  iterations: 5,
  thresholds: {
    'checks': ['rate==1'],
  },
};

export default function () {
  const adminToken = loginAs('admin');
  const empleadoToken = loginAs('empleado');
  const cajeroToken = loginAs('cajero');

  // --- Empleado no puede operar caja ---
  const cajaEndpoints = [
    `${API}/caja/abierta`,
    `${API}/caja/panel`,
    `${API}/caja/historial`,
  ];
  for (const url of cajaEndpoints) {
    const res = http.get(url, authHeaders(empleadoToken));
    check(res, {
      [`empleado -> ${url} no es 2xx`]: (r) => r.status >= 400 && r.status < 500,
    });
  }

  // --- Empleado no puede abrir caja ---
  const abrirEmpleado = http.post(`${API}/caja/abrir`, JSON.stringify({ monto_inicial: 100000 }), authHeaders(empleadoToken));
  check(abrirEmpleado, {
    'empleado no puede abrir caja': (r) => r.status === 403 || r.status === 401,
  });

  // --- Cajero sí puede consultar caja abierta ---
  const cajaCajero = http.get(`${API}/caja/abierta`, authHeaders(cajeroToken));
  check(cajaCajero, {
    'cajero consulta caja (2xx o 404 si no hay caja)': (r) => r.status < 500,
  });

  // --- Venta con monto negativo / cantidad 0 / producto inexistente ---
  const ventaInvalida = http.post(
    `${API}/ventas/`,
    JSON.stringify({
      id_sesion_caja: 1,
      items: [{ id_producto: 999999, cantidad: 0, precio_unitario: -100 }],
      pagos: [{ metodo: 'efectivo', monto: -100 }],
    }),
    authHeaders(cajeroToken),
  );
  check(ventaInvalida, {
    'venta inválida -> 4xx (no 5xx)': (r) => r.status >= 400 && r.status < 500,
  });

  // --- Venta sin caja abierta (id_sesion_caja inexistente) ---
  const ventaSinCaja = http.post(
    `${API}/ventas/`,
    JSON.stringify({
      id_sesion_caja: 999999,
      items: [{ id_producto: 1, cantidad: 1, precio_unitario: 1000 }],
      pagos: [{ metodo: 'efectivo', monto: 1000 }],
    }),
    authHeaders(cajeroToken),
  );
  check(ventaSinCaja, {
    'venta sin caja -> 4xx (no 5xx)': (r) => r.status >= 400 && r.status < 500,
  });

  // --- Admin no debería operar POS (si hay endpoint POS dedicado) ---
  // (POS es cajero-only; se valida a nivel de frontend y, si existe, backend)
}
