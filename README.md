# noswitch-pos-schedule

----English---An Idea of making a pos+calendar system, with a friendly interface so you and your employees can clearly see their shifts, and if someone can't do it, they can request replacement, and someone else can accept all the shift or half of it if that's the case.
---Spanish---
Una idea para crear un sistema de punto de venta y calendario, con una interfaz amigable para que usted y sus empleados puedan ver claramente sus turnos, y si alguien no puede hacerlo, puede solicitar un reemplazo, y otra persona puede aceptar todo el turno o la mitad si es necesario.

---Resultado---
Multi-sucursal POS con Facturación Electrónica DIAN, Workforce Management y Liquidación de Sueldos.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Celery
- **Database:** PostgreSQL 16 + Redis 7
- **Frontend:** Vue 3 + TypeScript + Pinia + Vite (PWA)
- **Deploy:** Docker Compose + Hostinger VPS(o cualquier deployer como vercel) + Caddy (auto-HTTPS)

## Quick Start (Development)

```bash
# 1. Clone and enter directory
cd pos-system

# 2. Copy environment
cp .env.example .env

# 3. Start services
docker compose up -d

# 4. Run seed (creates admin user + permissions)
docker compose exec api python -m scripts.seed

# 5. Access API docs
open http://localhost:8000/docs

# 6. Access PWA
cd pwa && npm install && npm run dev
open http://localhost:5173
```

## Default Users

| User | Document | Password | Role |
|------|----------|----------|------|
| Admin | 1000000000 | admin123 | administrador |
| Cajero | 1000000001 | cajero123 | cajero |

## Project Structure

```
pos-system/
├── app/                    # Backend Python (FastAPI)
│   ├── api/v1/            # API routes
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── tasks/             # Celery tasks
│   └── utils/             # ESC/POS, QR, DIAN XML
├── alembic/               # Database migrations
├── pwa/                   # Frontend Vue 3 PWA
├── tests/                 # pytest tests
├── scripts/               # Seed, utilities
├── Dockerfile.api         # API container
├── Dockerfile.worker      # Celery worker container
├── docker-compose.yml     # Development
└── docker-compose.prod.yml # Production
```

## Hardware

- **Ticketera:** 3nstar PTA0140 (USB/ESC/POS)
- **Cajón:** 3nstar compatible (RJ11 a impresora)

## RF Coverage

| RF | Status |
|----|--------|
| RF-1.1 Multi-código barras |  Model + API |
| RF-1.2 Ventas multimodales |  POS + pagos |
| RF-2.1 Acceso por turno |  Validación apertura |
| RF-2.2 Base por defecto |  Config parametrizable |
| RF-2.3 Doble panel |  Endpoint panel |
| RF-2.4 Alerta cierre |  Celery beat task |
| RF-2.5 Política arqueo |  Arqueo por denominación |
| RF-3.1 Calendario turnos |  CRUD + plantillas |
| RF-3.2 Solicitud móvil |  API + PWA |
| RF-3.3 Filtro + push |  Notificaciones PWA |
| RF-3.4 Control 44h |  Trigger + validación |
| RF-3.5 Fraccionamiento |  Pago proporcional |
| RF-3.6 Bypass emergencia |  Pendiente implementar |
| RF-4.1 Self-service sueldo |  Turnos pendientes |
| RF-4.2 Liquidación múltiple |  Selección múltiple |
| RF-4.3 QR dinámico |  EMVCo QR generator |
| RF-4.4 Doble comprobante |  Impresión ESC/POS |
