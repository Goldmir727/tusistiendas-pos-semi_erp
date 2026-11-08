// k6/lib/auth.js
// Helpers de autenticación reutilizables entre scripts.

import http from 'k6/http';
import { check } from 'k6';
import { API, USERS } from './config.js';

export function login(email, password) {
  const res = http.post(
    `${API}/auth/login`,
    JSON.stringify({ email, contrasena: password, recordar_dispositivo: false }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  let token = null;
  let refreshToken = null;
  try {
    const body = res.json();
    token = body.access_token || null;
    refreshToken = body.refresh_token || null;
  } catch (e) {
    // respuesta no JSON (ej. 5xx) -> token queda null
  }

  return { res, token, refreshToken };
}

export function loginAs(role) {
  const u = USERS[role];
  if (!u) throw new Error(`Rol desconocido: ${role}`);
  const { res, token } = login(u.email, u.password);
  check(res, {
    [`login ${role} ok`]: (r) => r.status === 200 && !!token,
  });
  return token;
}

export function authHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
}

// Token manipulado: cambia un carácter de la firma para que falle la verificación.
export function tamperToken(token) {
  if (!token) return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.signature';
  const parts = token.split('.');
  if (parts.length !== 3) return token + 'x';
  const sig = parts[2];
  const last = sig.charAt(sig.length - 1);
  const swapped = last === 'a' ? 'b' : 'a';
  parts[2] = sig.slice(0, -1) + swapped;
  return parts.join('.');
}
