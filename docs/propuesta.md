# Propuesta: Sistema POS Multi-Sucursal (v2)

## 1. Vision general

Sistema integral de punto de venta para negocio colombiano con multiples sucursales, que reemplaza al sistema anterior. Cubre la operacion completa del dia a dia: venta en mostrador, caja, inventario, compras, devoluciones, clientes a credito (fiado), turnos de empleados, nomina y facturacion electronica DIAN.

**Stack tecnico**

- Backend: Python 3.11 / FastAPI / PostgreSQL 16 / Redis / Celery
- Frontend: Vue 3 (PWA instalable en moviles) + API REST con Swagger (`/docs`)
- Hardware: impresora termica 3nstar PTA0140 + gaveta de dinero (RJ11)
- Infraestructura: VPS Hostinger, Docker Compose, HTTPS automatico (Caddy)
- Facturacion electronica DIAN: homologacion desde el dia 1, produccion despues

**Roles**

- Administrador: acceso total (configuracion, aprobaciones, reportes, usuario, sueldos)
- Cajero: venta, caja, consulta de turnos/pagos, clientes, compras, devoluciones (con limites)

---

## 2. Requerimientos funcionales

### 2.1 Autenticacion y seguridad
- Login con **email + contrasena** (contrasenas **hasheadas con bcrypt**, nunca en claro)
- Tokens JWT de acceso (30 min) y refresco (7 dias) por dispositivo, revocables
- Proteccion contra fuerza bruta: maximo 5 intentos y bloqueo de 5 minutos por IP
- Acceso por rol: administrador / cajero
- Todas las claves y secretos viven en `.env`, nunca en el codigo

### 2.2 Venta en mostrador (POS)
- Escaneo de **codigo de barras** (multiples codigos por producto)
- Medios de pago: **Efectivo, Tarjeta, Nequi, Daviplata, PSE y Fiado**
- Cliente opcional en la venta (consumidor final por defecto, o cliente identificado para DIAN)
- Doble comprobante termico (tiquete al cliente + copia)
- Factura electronica DIAN para toda venta, incluida la venta a credito

### 2.3 Caja (panel doble)
- Abrir/cerrar sesion de caja por turno con base inicial
- Conteo por denominaciones (arqueo) al cerrar y calculo de **descuadre**
- **Egresos de caja** (renta, servicios, insumos, retiros) asociados a la sesion abierta
- El efectivo esperado al cierre = base inicial + ventas en efectivo - egresos
- Corte diario (reporte Z): ventas por medio de pago, devoluciones, egresos y descuadres

### 2.4 Productos e inventario
- Precio de venta calculado automaticamente: costo + margen de ganancia (%) configurable
- Margen por producto individual (puede anular el default)
- Alerta de **stock critico** cuando el inventario cae al minimo
- Historial de movimientos de stock (entrada, salida, ajuste, merma, devolucion)

### 2.5 Compras y reposicion
- Catalogo de **proveedores** (nombre, NIT, contacto)
- Registro de compra al recibir mercancia: sube stock y actualiza el **costo promedio ponderado**
- Lista de productos por reponer (los que estan en stock critico)

### 2.6 Clientes y credito (fiado)
- Catalogo de clientes con datos fiscales (para facturacion DIAN)
- Venta a fiado: se asigna al cliente, queda como deuda
- **Cuenta corriente** por cliente: saldo deudor, historial de ventas y abonos
- Abonos contra una venta especifica o contra el saldo global
- Reporte de **cartera** (quien debe y cuanto)

### 2.7 Devoluciones y nota de credito DIAN
- Devolucion total o parcial de una venta: repone stock y revierte la caja
- **Nota de credito** (documento DIAN independiente y numerado) referenciando la factura original
- **Reglas por rol**: el cajero puede auto-devolver hasta un monto configurable por turno; lo que exceda requiere aprobacion del administrador
- Devolucion de venta a fiado descuenta el saldo del cliente (no devuelve efectivo)

### 2.8 Turnos y fuerza de trabajo
- Calendario interactivo estilo Google Calendar (vista semanal por horas)
- Creacion con un click, turnos que cruzan medianoche, navegacion semanal
- Rango horario configurable (locales 24/7)
- Lugar legal de **44 horas semanales** por empleado (validado en asignacion y reemplazo)
- Solicitud y aprobacion de reemplazo

### 2.9 Pagos de sueldo
- Liquidacion sobre turnos finalizados, pago en efectivo o transferencia (registrada fuera del sistema)
- QR dinamico para cobro de sueldo

### 2.10 Reportes (solo administrador)
- Ventas por dia, stock critico, descuadres de caja, cartera de fiado, corte diario (Z)

---

## 3. Casos de uso principales

- **CU-01 Login con email:** usuario ingresa email + contrasena → se verifica el hash → se emiten los tokens JWT.
- **CU-02 Venta de mostrador:** escanear productos → elegir medio de pago → validar stock y caja abierta → factura DIAN + doble tiquete.
- **CU-03 Venta a fiado:** seleccionar cliente y medio "fiado" → la venta queda pendiente y suma a la cuenta del cliente; el stock baja de inmediato.
- **CU-04 Abono de fiado:** registrar pago contra una venta o contra el saldo → baja el saldo deudor; si queda saldo en cero la venta pasa a pagada.
- **CU-05 Devolucion rapida (cajero):** seleccionar venta y items → dentro del limite se aprueba sola, repone stock, revierte caja y genera nota de credito.
- **CU-06 Devolucion con aprobacion (admin):** el monto excede el limite del cajero → queda pendiente y el administrador la aprueba o rechaza.
- **CU-07 Registrar compra:** recibir mercancia de un proveedor → sube stock y actualiza el costo promedio.
- **CU-08 Reponer stock:** el reporte marca productos criticos → desde ahi se crea la compra.
- **CU-09 Registro de egreso:** sobre la caja abierta se registran gastos → al cerrar se descuentan del efectivo esperado.
- **CU-10 Corte diario:** el administrador consulta el resumen Z del dia.
- **CU-11 Crear turno:** click en la franja del calendario → validar 44 horas → guardar.
- **CU-12 Pago de sueldo:** seleccionar turnos finalizados → pagar en efectivo o transferencia.

---

## 4. Modelo de datos (resumen)

- `usuarios`, `roles` y `permisos`, `sesiones_usuario`
- `sucursales`, `puntos_venta`
- `productos`, `codigos_barras`, `movimientos_stock`
- `proveedores`, `compras`, `compra_detalle`
- `clientes`, `ventas`, `venta_detalle`, `venta_pago`, `abonos_cliente`
- `devoluciones`, `devolucion_detalle`
- `sesiones_caja`, `caja_arqueo`, `cortes_diarios`, `egresos`
- `turnos_calendario`, `turnos_plantilla`, `festivos`, `notificaciones`
- `pagos_sueldos`, `pago_turno_detalle`
- `comprobantes`, `numeracion_dian`
- `configuracion` (parametros globales: margen default, horario del calendario, limite de devolucion)

---

## 5. Notas operativas

- El stock se descuenta **al momento de la venta**, no al abonar.
- El fiado no entra en el conteo de la caja hasta que se abona en efectivo/digital.
- Las devoluciones y notas de credito son procesos auditables (queda registrado quien solicita y quien aprueba).
- Se usa **costo promedio ponderado** para valorar inventario al registrar compras.
- Configuracion clave por defecto: `devoluciones.max_por_turno_cajero = 50000` (ajustable desde el panel de administrador).
