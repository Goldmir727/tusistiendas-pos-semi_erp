// k6/auth_bruteforce.js
// Tests de seguridad: brute-force, enumeración de usuarios, token tampering y alg:none.
//
// Ejecutar:
//   k6 run -e BASE_URL=http://localhost:8000 k6/auth_bruteforce.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { API } from './lib/config.js';
import { login, loginAs, tamperToken } from './lib/auth.js';

export const options = {
  scenarios: {
    brute_force: {
      executor: 'constant-arrival-rate',
      exec: 'bruteForce',
      rate: 15,
      timeUnit: '1s',
      duration: '20s',
      preAllocatedVUs: 10,
    },
    token_tampering: {
      executor: 'per-vu-iterations',
      exec: 'tokenTampering',
      vus: 3,
      iterations: 5,
      startTime: '22s',
    },
  },
  thresholds: {
    'checks': ['rate==1'],
  },
};

export function bruteForce() {
  const email = Math.random() < 0.5 ? 'admin@pos.com' : 'noexiste@pos.com';
  const res = http.post(
    `${API}/auth/login`,
    JSON.stringify({ email, contrasena: 'wrong-' + Math.random() }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(res, {
    'login inválido no es 5xx': (r) => r.status < 500,
    'no enumera usuarios (mensaje genérico)': (r) => {
      const b = (r.body || '').toLowerCase();
      return !b.includes('no existe') && !b.includes('user not found') && !b.includes('usuario no encontrado');
    },
    'no filtra devCode': (r) => !(r.body || '').includes('devCode') && !(r.body || '').includes('dev_code'),
    'respuesta 401 o 429': (r) => r.status === 401 || r.status === 429,
  });
  sleep(0.05);
}

export function tokenTampering() {
  const token = loginAs('admin');
  if (!token) return;

  const tampered = tamperToken(token);
  const res = http.get(`${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-07`, {
    headers: { Authorization: `Bearer ${tampered}` },
  });

  check(res, {
    'token alterado -> 401': (r) => r.status === 401,
    'sin datos filtrados': (r) => !(r.body || '').includes('id_turno'),
  });

  // Token con alg:none
  const noneToken = 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIiwicm9sIjoiYWRtaW5pc3RyYWRvciJ9.';
  const res2 = http.get(`${API}/turnos/calendario?fecha_desde=2026-11-01&fecha_hasta=2026-11-07`, {
    headers: { Authorization: `Bearer ${noneToken}` },
  });
  check(res2, { 'alg:none -> 401': (r) => r.status === 401 });
}
