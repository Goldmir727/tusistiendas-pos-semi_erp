# Tests de seguridad con Grafana k6

Scripts de seguridad para el backend del POS/ERP (FastAPI). Se ejecutan contra
una instancia local o de staging; **nunca contra producción con datos reales**.

## Instalación de k6

```powershell
winget install GrafanaLabs.k6
# o
choco install k6
# o
scoop install k6
```

Verificación:
```powershell
k6 version
```

## Estructura

```
k6/
  lib/
    config.js        # BASE_URL, usuarios y IDs de prueba
    auth.js          # login, tokens, tampering
  auth_bruteforce.js # brute-force, enumeración, token tampering, alg:none
  rbac_idor.js       # roles, IDOR entre usuarios/sucursales, sin token
  injection.js       # SQLi, path traversal, XSS, payloads grandes
  headers_cors.js    # cabeceras, CORS, docs/openapi
  pos_caja.js        # POS y caja: roles, caja abierta, validaciones
```

## Ejecución

Variables de entorno (opcionales):

| Variable | Default |
|---|---|
| `BASE_URL` | `http://localhost:8000` |
| `ADMIN_EMAIL` | `admin@pos.com` |
| `ADMIN_PASSWORD` | `admin123` |
| `EMPLEADO_EMAIL` | `empleado01@pos.com` |
| `EMPLEADO_PASSWORD` | `empleado123` |
| `CAJERO_EMAIL` | `cajero01@pos.com` |
| `CAJERO_PASSWORD` | `cajero123` |

Ejemplos:

```powershell
# Todos los scripts contra local
k6 run -e BASE_URL=http://localhost:8000 k6/auth_bruteforce.js
k6 run -e BASE_URL=http://localhost:8000 k6/rbac_idor.js
k6 run -e BASE_URL=http://localhost:8000 k6/injection.js
k6 run -e BASE_URL=http://localhost:8000 k6/headers_cors.js
k6 run -e BASE_URL=http://localhost:8000 k6/pos_caja.js
```

Generar reporte JSON:
```powershell
k6 run --out json=results.json -e BASE_URL=http://localhost:8000 k6/rbac_idor.js
```

## Criterios de fallo

Cada script define `thresholds`. El pipeline de CI falla si:
- Algún request produce `5xx`.
- Un check de seguridad no se cumple (ej. token alterado no da 401, IDOR filtra datos, SQLi produce 5xx).

## Lo que NO cubre k6

- Escaneo automático de vulnerabilidades (usar OWASP ZAP / nuclei).
- Auditoría de dependencias (`pip-audit`, `npm audit`).
- Revisión estática (bandit, ruff security rules).
- Pruebas manuales de 2FA real (requiere SMTP configurado).

## Usuarios de prueba

Los scripts usan los usuarios del seed (`scripts/seed.py`). Asegúrate de haber
ejecutado el seed antes de correr los tests.
