// k6/lib/config.js
// Configuración compartida para los tests de seguridad.
//
// Uso:
//   k6 run -e BASE_URL=http://localhost:8000 k6/auth_bruteforce.js
//   k6 run -e BASE_URL=https://tusistiendas-pos-semierp.vercel.app k6/headers_cors.js
//
// Variables de entorno:
//   BASE_URL        URL base del API (sin slash final). Default: http://localhost:8000
//   ADMIN_EMAIL     Email del admin de prueba. Default: admin@pos.com
//   ADMIN_PASSWORD  Password del admin de prueba. Default: admin123
//   EMPLEADO_EMAIL  Email de empleado de prueba. Default: empleado01@pos.com
//   EMPLEADO_PASSWORD Password de empleado de prueba. Default: empleado123
//   CAJERO_EMAIL    Email de cajero de prueba.
//   CAJERO_PASSWORD Password de cajero de prueba.

export const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export const USERS = {
  admin: {
    email: __ENV.ADMIN_EMAIL || 'admin@pos.com',
    password: __ENV.ADMIN_PASSWORD || 'admin123',
  },
  empleado: {
    email: __ENV.EMPLEADO_EMAIL || 'empleado01@pos.com',
    password: __ENV.EMPLEADO_PASSWORD || 'empleado123',
  },
  cajero: {
    email: __ENV.CAJERO_EMAIL || 'cajero@pos.com',
    password: __ENV.CAJERO_PASSWORD || 'cajero123',
  },
};

// IDs de prueba (ajustar si el seed cambia). Se usan para intentos de IDOR.
export const IDS = {
  empleadoPropio: 6,   // Ana Maria Rodriguez (seed)
  empleadoOtro: 7,     // Carlos Andres Gomez (seed)
  sucursalPropia: 1,   // Tienda Principal
  sucursalOtra: 2,     // Sucursal Norte
};

export const API = `${BASE_URL}/api/v1`;
