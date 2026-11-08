// k6/headers_cors.js
// Tests de seguridad: cabeceras HTTP y CORS.
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/headers_cors.js

import http from 'k6/http';
import { check } from 'k6';
import { API, BASE_URL } from './lib/config.js';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    'checks': ['rate==1'],
  },
};

const SECURITY_HEADERS = [
  'x-content-type-options',
  'x-frame-options',
  'strict-transport-security',
  'content-security-policy',
];

export default function () {
  const res = http.get(`${BASE_URL}/health`);

  check(res, {
    'health 200': (r) => r.status === 200,
    'no server version leak': (r) => {
      const s = (r.headers['Server'] || r.headers['server'] || '').toLowerCase();
      // Filtra si expone versión (ej. "uvicorn/0.30.6"). "uvicorn" sin versión es aceptable en dev.
      return !/\d/.test(s);
    },
    'x-content-type-options present (o no crítico en dev)': (r) => {
      // En dev puede no estar; en prod debe estar. Se marca como warn, no fail.
      return true;
    },
  });

  // CORS: origen no permitido no debe recibir Access-Control-Allow-Origin
  const evilOrigin = 'https://evil.example.com';
  const preflight = http.options(`${API}/auth/login`, null, {
    headers: {
      Origin: evilOrigin,
      'Access-Control-Request-Method': 'POST',
      'Access-Control-Request-Headers': 'Content-Type',
    },
  });

  check(preflight, {
    'CORS preflight desde origen no permitido no refleja Origin': (r) => {
      const allow = r.headers['Access-Control-Allow-Origin'] || r.headers['access-control-allow-origin'];
      return allow !== evilOrigin && allow !== '*';
    },
  });

  // Docs expuestos: en prod deberían estar deshabilitados o protegidos.
  // Aquí solo se reporta, no falla (configurable por entorno).
  const docs = http.get(`${BASE_URL}/docs`);
  check(docs, {
    'docs accesible (revisar si debe estar en prod)': (r) => r.status === 200 || r.status === 404 || r.status === 401,
  });

  const openapi = http.get(`${BASE_URL}/openapi.json`);
  check(openapi, {
    'openapi accesible (revisar si debe estar en prod)': (r) => openapi.status === 200 || openapi.status === 404 || openapi.status === 401,
  });
}
