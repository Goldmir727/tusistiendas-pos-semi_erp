# Propuesta de sistema POS y gestión operativa para tiendas

---

**Producto:** TuSisTiendas
**Empresa:** NoSwitch
**Versión:** 0.1 — Versión comercial para cliente
**Fecha:** 16 de agosto de 2026
**Autor:** Johan Stiven Grisales Vargas

---

## 1. Resumen ejecutivo

TuSisTiendas es un sistema tipo POS y ERP ligero (Planificación de Recursos Empresariales) desarrollado por NoSwitch, diseñado para automatizar procesos repetitivos y centralizar la operación diaria de tiendas, quioscos y misceláneas que manejan empleados y un flujo constante de clientes.

TuSisTiendas no es solo un sistema POS. La solución integra la gestión de ventas con los procesos internos del negocio para simplificar su operación diaria: quién abrió la caja, quién está trabajando, quién reemplazó a quién, qué ocurrió durante el turno, cómo se realizó el cierre y cómo se mantiene la operación ante fallos de conexión o energía.

En su primera versión, la solución incluye registro de ventas, ventas temporales, ventas a crédito (fiado), gestión de productos e inventario, compras y proveedores, apertura y cierre de caja con arqueo, egresos, devoluciones, facturación electrónica DIAN, asignación de turnos y reemplazos, liquidación básica de nómina sobre turnos finalizados, gestión de clientes y reportes administrativos. Todo desde una aplicación multiplataforma basada en tecnología PWA.

> **Propuesta de valor:** TuSisTiendas no es solo un sistema POS; integra la gestión de ventas con los procesos internos del negocio para simplificar su operación diaria.

---

## 2. Contexto y problemática actual

El negocio opera actualmente con un sistema POS llamado **TiendasOn**, que apoya los procesos de ventas e inventario. Durante su uso se han identificado falencias que afectan directamente la operación diaria:

**Problema 1 — Escaneo de productos.**
El sistema interpreta accidentalmente códigos QR como entrada durante el proceso de venta. Si la venta no fue guardada como temporal, la aplicación se cierra y la venta se pierde por completo.

**Problema 2 — Cierre de caja.**
El proceso de cierre exige realizar un ajuste de inventario para poder cerrar la caja, lo que genera alertas repetitivas y aumenta el tiempo requerido para el cierre.

**Problema 3 — Gestión de ventas temporales.**
El sistema no permite diferenciar con claridad las ventas que aún no han sido finalizadas, lo que provoca confusión al retomarlas o su eliminación accidental.

**Problema 4 — Dependencia de conexión y energía.**
El sistema depende por completo de la conexión a Internet para operar, por lo que una interrupción de red puede detener por completo la operación del negocio.

Estas situaciones provocan pérdidas económicas por ventas mal registradas o perdidas, errores en inventario y cuadre de caja, pérdida de tiempo en procesos repetitivos, falta de control sobre la operación diaria e imposibilidad de operar ante interrupciones del servicio.

---

## 3. Necesidades identificadas

A partir de la situación actual, el negocio necesita:

1. Registrar ventas de forma rápida y confiable, sin riesgo de perder información por errores de escaneo o cierres inesperados.
2. Diferenciar claramente las ventas temporales de las ventas finalizadas.
3. Realizar apertura y cierre de caja de forma ágil, con arqueo claro y sin pasos innecesarios.
4. Mantener la operación de ventas ante fallos de conexión a Internet, con sincronización posterior.
5. Centralizar en una sola plataforma las ventas, el inventario, los clientes, la caja, los turnos y la nómina básica.
6. Contar con reportes claros para la toma de decisiones: ventas por día, descuadres, cartera y corte diario.
7. Cumplir con la facturación electrónica DIAN en ventas y devoluciones.

---

## 4. Propuesta de solución: TuSisTiendas

TuSisTiendas es un sistema de punto de venta y gestión empresarial desarrollado por NoSwitch, orientado a pequeñas y medianas tiendas, que permite centralizar las operaciones de ventas, inventario, clientes, caja, turnos, nómina básica y reportes mediante una plataforma web/PWA.

La solución permitirá al negocio:

- Registrar ventas con escaneo de código de barras y múltiples medios de pago.
- Gestionar ventas temporales, ventas a crédito (fiado) y devoluciones.
- Administrar productos, inventario, compras y proveedores.
- Realizar apertura y cierre de caja con arqueo por denominaciones y registro de egresos.
- Asignar turnos y gestionar reemplazos de empleados, con control de 44 horas semanales.
- Liquidar pagos a empleados sobre turnos finalizados.
- Emitir factura electrónica DIAN y notas de crédito.
- Consultar reportes administrativos del día a día.
- Operar desde tablets y computadores, con funcionamiento offline y sincronización posterior.

La solución está dirigida a administradores, encargados de tienda y cajeros, con permisos diferenciados según su rol.

---

## 5. Beneficios para el cliente

**Para el negocio, TuSisTiendas permitirá:**

- Eliminar ventas perdidas por errores de escaneo o cierres inesperados.
- Agilizar el cierre de caja sin ajustes de inventario innecesarios.
- Centralizar turnos, reemplazos, caja y ventas en una única plataforma.
- Mantener la atención al público incluso ante fallos de conexión.
- Tomar decisiones con reportes claros de ventas, caja, inventario y cartera.

**Para los empleados, el sistema permitirá:**

- Utilizar una interfaz intuitiva que reduce el tiempo de capacitación.
- Dedicar menos tiempo a tareas repetitivas y más tiempo a la atención al cliente.
- Consultar con claridad sus turnos, reemplazos y pagos.
- Trabajar desde cualquier dispositivo autorizado del negocio.

**Para los clientes del negocio, la solución permitirá:**

- Recibir una atención más rápida en mostrador.
- Recibir comprobantes y facturas electrónicas sin errores.
- Encontrar el negocio disponible incluso ante fallas técnicas.

---

## 6. Alcance del proyecto

El proyecto contempla el desarrollo, la implementación y la puesta en marcha de la primera versión de TuSisTiendas para el negocio cliente, incluyendo:

- Sistema de ventas POS con facturación electrónica DIAN.
- Gestión de productos, inventario, compras y proveedores.
- Gestión de clientes y ventas a crédito (fiado) con cuenta corriente y abonos.
- Módulo de caja: apertura, cierre con arqueo, egresos, devoluciones y corte diario.
- Módulo de turnos: calendario semanal, reemplazos y control de 44 horas.
- Liquidación básica de nómina sobre turnos finalizados.
- Gestión de usuarios y permisos por rol.
- Reportes administrativos esenciales.
- Instalación en 3 terminales POS, configuración del servidor, carga inicial y capacitación.

El detalle de funcionalidades incluidas, no incluidas y futuras se presenta en las secciones 7, 18 y 19.

---

## 7. Funcionalidades incluidas

### 7.1 Ventas en mostrador (POS)

- Escaneo de código de barras, con soporte de múltiples códigos por producto.
- Medios de pago: efectivo, transferencia, datáfono y pago mixto. El pago mixto abre un modal que permite registrar varios pagos a la vez para completar el total de la venta. Adicionalmente, el sistema permite la venta a fiado (crédito), descrita en la sección de clientes y crédito.
- Cliente opcional en la venta (consumidor final por defecto o cliente identificado para DIAN).
- Ventas temporales con persistencia: no se pierden al cerrar la aplicación.
- Doble comprobante térmico (tiquete para el cliente + copia).
- Factura electrónica DIAN para toda venta, incluida la venta a crédito.

### 7.2 Productos e inventario

- Creación, consulta, actualización y eliminación de productos.
- Precio de venta calculado automáticamente a partir del costo más un margen de ganancia configurable, con posibilidad de definir margen por producto.
- Alerta de stock crítico cuando el inventario cae al mínimo.
- Historial de movimientos de stock (entrada, salida, ajuste, merma, devolución).

### 7.3 Compras y reposición

- Catálogo de proveedores (nombre, NIT, contacto).
- Registro de compra al recibir mercancía, con actualización de stock y de costo promedio.
- Lista de productos por reponer a partir del stock crítico.

### 7.4 Clientes y crédito (fiado)

- Catálogo de clientes con datos fiscales para facturación DIAN.
- Venta a fiado asignada al cliente, con descuento inmediato de stock.
- Cuenta corriente por cliente: saldo deudor, historial de ventas y abonos.
- Abonos contra una venta específica o contra el saldo global.
- Reporte de cartera (quién debe y cuánto).

### 7.5 Caja

- Apertura y cierre de sesión de caja por turno, con base inicial.
- Conteo por denominaciones (arqueo) al cierre, con cálculo de descuadre.
- Registro de egresos de caja (renta, servicios, insumos, retiros) asociados a la sesión abierta.
- Cálculo de efectivo esperado: base inicial + ventas en efectivo − egresos.
- Corte diario (reporte Z): ventas por medio de pago, devoluciones, egresos y descuadres.

### 7.6 Devoluciones y nota de crédito DIAN

- Devolución total o parcial de una venta, con reposición de stock y reversión en caja.
- Nota de crédito como documento DIAN independiente y numerado, referenciando la factura original.
- Reglas por rol: el cajero puede auto-devolver hasta un monto configurable por turno; los montos superiores requieren aprobación del administrador.
- La devolución de una venta a fiado descuenta el saldo del cliente.

### 7.7 Turnos y reemplazos

- Calendario interactivo con vista semanal por horas.
- Creación de turnos ágil, incluyendo turnos que cruzan medianoche.
- Rango horario configurable.
- Validación de 44 horas semanales por empleado en asignación y reemplazos.
- Solicitud y aprobación de reemplazos.
- Notificaciones de turnos y reemplazos.

### 7.8 Nómina básica

- Liquidación sobre turnos finalizados.
- Registro de pago en efectivo o transferencia.
- QR dinámico para cobro de sueldo.

### 7.9 Usuarios y permisos

- Acceso con email y contraseña.
- Roles diferenciados:
  - **Administrador:** acceso total, configuración, aprobaciones, reportes, gestión de usuarios, turnos y nómina.
  - **Cajero:** ventas, caja, egresos, clientes y crédito, compras, devoluciones dentro del límite, turnos y comprobantes.
- Bloqueo temporal ante intentos fallidos reiterados.

### 7.10 Reportes

- Ventas por día, por medio de pago y por empleado.
- Stock crítico.
- Descuadres de caja.
- Cartera de fiado.
- Corte diario (Z).
- Turnos y horas trabajadas.

El acceso a reportes administrativos está reservado al rol administrador.

### 7.11 Configuración

- Parámetros globales configurables (margen por defecto, horario del calendario, límite de devolución de cajero, entre otros).
- Gestión de usuarios.
- Configuración de facturación electrónica DIAN.

---

## 8. Experiencia de usuario y funcionamiento

El diseño de TuSisTiendas prioriza claridad, eficiencia y consistencia, con flujos optimizados para la operación diaria en mostrador.

- **Acceso:** pantalla de ingreso simple con email y contraseña, mensajes de error claros y diseño con identidad TuSisTiendas.
- **Panel principal:** resumen del día con ventas totales, estado de caja y turnos activos, además de accesos rápidos y notificaciones pendientes.
- **Pantalla de ventas:** campo de escaneo destacado, lista de productos con cantidades y subtotales, total siempre visible y botones amplios para medios de pago y venta temporal.
- **Pantalla de caja:** paneles diferenciados para apertura, cierre con arqueo por denominaciones, registro rápido de egresos y resumen de la sesión.
- **Calendario de turnos:** vista semanal con colores por empleado, indicadores de horas acumuladas y solicitud de reemplazo accesible.
- **Reportes:** filtros por fecha, empleado y medio de pago, con opción de exportación.

La interfaz es responsive: funciona en computador de mostrador, tablet y móvil (PWA), adaptando la densidad de información a cada dispositivo.

---

## 9. Funcionamiento offline y continuidad operativa

La aplicación está construida como PWA instalable, lo que permitirá al negocio:

- Continuar registrando ventas y operaciones críticas aunque se pierda la conexión a Internet.
- Conservar las ventas temporales y los datos de la sesión en el dispositivo.
- Sincronizar automáticamente la información cuando la conexión se restablezca.
- Recuperar sesiones interrumpidas sin pérdida de información.

De esta manera, el negocio podrá mantener la atención al público ante fallos de conexión, reduciendo detenciones operativas.

---

## 10. Hardware requerido

La inversión contempla el hardware necesario para operar 3 puestos de venta:

- **3 terminales POS 3nStar PTA0140** (con impresora térmica incorporada), a $1.800.000 cada una.

Los cajones de dinero y los lectores de código de barras son aportados por el negocio.

El hardware corresponde a una inversión realizada por el cliente por un valor total de **$5.400.000**, más los cobros por domicilio que puedan aplicar según la ubicación del negocio. La configuración e instalación de estos equipos está incluida dentro del valor de implementación inicial y no se cobra por separado.

---

## 11. Arquitectura y tecnología

Para brindar confianza sobre la solución, se presenta un resumen no técnico de la tecnología utilizada:

- **Aplicación (PWA):** funciona en navegador moderno e instalable en tablets y computadores, sin depender de un sistema operativo específico.
- **Servidor:** plataforma central que concentra ventas, inventario, caja, turnos y reportes, con despliegue controlado y actualizaciones verificadas.
- **Base de datos:** almacenamiento central y estructurado de toda la operación del negocio.
- **Facturación electrónica:** integración con DIAN, con etapa inicial de homologación y posterior paso a producción.
- **Impresión:** compatibilidad con impresora térmica 3nStar PTA0140.

Detalle técnico de referencia: backend en Python / FastAPI, base de datos PostgreSQL, frontend en Vue 3 + TypeScript como PWA, infraestructura con Docker y HTTPS automático.

---

## 12. Identidad del producto

TuSisTiendas utiliza una identidad visual tecnológica y comercial basada en azul marino y cyan, que transmite confianza, estabilidad e innovación.

**Colores de referencia:**

| Color | Uso | HEX |
|-------|-----|-----|
| Azul marino tecnológico | Texto principal e identidad corporativa | #06234B |
| Cyan / Turquesa | Elementos destacados, innovación y crecimiento | #08CFE3 |
| Azul medio | Transiciones y elementos secundarios | #1676B8 |
| Azul claro | Variaciones y degradados | #29A9D6 |
| Blanco | Fondo principal y versiones invertidas | #FFFFFF |
| Negro | Versión monocromática e impresión | #000000 |

Degradado representativo: `#06234B → #1676B8 → #08CFE3` (estabilidad → evolución → crecimiento).

**Tipografías de referencia:** Montserrat para identidad de marca e Inter para interfaces, formularios, tablas y documentación.

**Logotipo:** isotipo abstracto con formas geométricas ascendentes y flecha hacia arriba, que representa crecimiento, progreso, aumento de ventas y organización. Incluye el descriptor "by NoSwitch". Se contemplan variantes a color, monocromática, isotipo solo, icono para PWA y versión simplificada para impresión de tickets.

> Nota: los valores HEX y la tipografía son de referencia visual. Para una guía de marca definitiva conviene extraerlos del archivo vectorial original del logo.

---

## 13. Seguridad y respaldo de información

La solución incluye medidas para proteger la información del negocio:

- Contraseñas almacenadas de forma cifrada (nunca en texto plano).
- Sesiones con expiración y revocación por dispositivo.
- Acceso diferenciado por rol (administrador / cajero).
- Protección contra intentos reiterados de acceso no autorizado.
- Comunicación cifrada HTTPS en producción.
- Registro de auditoría de acciones críticas (quién realizó cada operación relevante).
- Copias de seguridad automáticas diarias de la base de datos con retención de 30 días.
- Respaldo local en el dispositivo para operación offline.

---

## 14. Implementación y puesta en marcha

La implementación inicial incluye:

1. Configuración e instalación de las 3 terminales POS.
2. Configuración del servidor y despliegue del sistema.
3. Carga inicial de productos e inventario.
4. Capacitación del personal administrativo y de cajeros.
5. Pruebas de funcionamiento y ajustes finales.

El proceso de actualización del sistema se realiza de forma controlada y verificada, para no interrumpir la operación del negocio.

---

## 15. Soporte, mantenimiento y actualizaciones

La mensualidad del servicio incluye:

- Infraestructura y disponibilidad del sistema.
- Mantenimiento y actualizaciones del sistema.
- Soporte técnico básico.
- Copias de seguridad automatizadas.
- Monitoreo básico de disponibilidad y revisión de errores.

Los límites del soporte, tiempos de respuesta, garantía y condiciones de terminación deberán definirse formalmente antes de la firma (ver Anexo B).

---

## 16. Plan de trabajo

**Fase 1 — MVP (meses 1 a 6).**

- Meses 1-2, fundamentos: arquitectura base, autenticación y roles, gestión básica de productos y clientes, estructura base de la PWA.
- Meses 3-4, POS central: ventas con código de barras, múltiples medios de pago, caja con arqueo, ventas temporales e impresión de comprobantes.
- Meses 5-6, gestión operativa: calendario de turnos, reemplazos, control de 44 horas, liquidación básica de nómina y reportes esenciales.

**Fase 2 — Estabilización y mejoras (meses 7 a 9).**

- Facturación electrónica DIAN.
- Devoluciones con nota de crédito.
- Optimización del funcionamiento offline.
- Pruebas con el negocio, ajustes de interfaz y documentación de usuario.

**Fase 3 — Evolución futura.**

- Funcionalidades descritas en la sección 19, según acuerdo posterior.

---

## 17. Inversión y modelo de precios

| Concepto | Valor |
|----------|-------|
| 3 terminales POS 3nStar PTA0140 (x3) | $5.400.000 (pago único) |
| Implementación inicial | $2.500.000 (pago único) |
| Mensualidad primer año | $36.960/mes |
| Mensualidad desde el segundo año | $69.550/mes |

> Los valores son precios finales para el cliente por los conceptos indicados. El valor de las terminales POS puede estar sujeto a cobros adicionales por domicilio (transporte de los equipos) según la ubicación del negocio. No incluyen costos variables de terceros que, de aplicar, se definirán por separado (ver sección 20).

---

## 18. Qué incluye la inversión

**Las 3 terminales POS ($5.400.000) incluyen:**

- 3 terminales 3nStar PTA0140 con impresora térmica incorporada, a $1.800.000 cada una.

El hardware quedará en propiedad del cliente una vez realizado el pago. Los cajones de dinero y los lectores de código de barras son aportados por el negocio y no forman parte de este valor. El valor de las terminales puede estar sujeto a cobros adicionales por domicilio según la ubicación del negocio.

**La implementación inicial ($2.500.000) incluye:**

- Configuración e instalación de las 3 terminales POS.
- Configuración del servidor y despliegue del sistema.
- Carga inicial de productos e inventario.
- Capacitación del personal administrativo y cajeros.
- Pruebas de funcionamiento y ajustes finales.

**La mensualidad incluye:**

- Disponibilidad del sistema e infraestructura.
- Mantenimiento y actualizaciones del sistema.
- Soporte técnico básico.
- Copias de seguridad automatizadas.

---

## 19. Qué NO está incluido

En esta primera versión no están incluidos:

- Módulo de Recursos Humanos completo (contratación, vacaciones, incapacidades).
- Nómina avanzada (bonificaciones, deducciones complejas, prestaciones legales).
- Cajones de dinero y lectores de código de barras (los aporta el negocio).
- Domicilio o transporte de los equipos, cuando aplique según la ubicación del negocio.
- Gestión de múltiples sucursales.
- Aplicación móvil nativa para iOS/Android (la solución se entrega como PWA instalable).
- Integración con pasarelas de pago externas.
- Módulo de contabilidad.
- Reportes personalizados avanzados.
- API pública para terceros.

---

## 20. Funcionalidades futuras

Podrán evaluarse en versiones posteriores, previo acuerdo y cotización separada:

- Gestión de múltiples sucursales.
- Aplicación móvil nativa.
- Integración con sistemas de pago externos.
- Reportes personalizados avanzados.
- Módulo de contabilidad básica.
- API pública para integraciones.
- Notificaciones push avanzadas.

Ninguna de estas funcionalidades forma parte del alcance ni del precio de la primera versión.

---

## 21. Condiciones y consideraciones

1. Los precios indicados corresponden a los conceptos descritos en las secciones 17 y 18.
2. El hardware es adquirido por el cliente y quedará de su propiedad. Los cajones de dinero y los lectores de código de barras son aportados por el negocio.
3. El valor de las terminales POS puede estar sujeto a cobros adicionales por domicilio (transporte de los equipos), según la ubicación del negocio.
4. La mensualidad del primer año es de $36.960 y desde el segundo año es de $69.550, según el modelo vigente.
5. Los costos variables de terceros (por ejemplo, facturación electrónica por documento, SMS, almacenamiento adicional o comisiones de pago) no están incluidos en la mensualidad y deberán definirse por separado si llegan a aplicar.
6. Antes de la firma deberán definirse formalmente: duración mínima del servicio, forma y fechas de pago, alcance exacto del soporte, garantía, tiempos de respuesta, propiedad del software, tratamiento de datos, y condiciones de terminación. Ver detalle en Anexo B.

---

## 22. Conclusiones

TuSisTiendas permitirá al negocio superar las limitaciones del sistema actual (TiendasOn), centralizando ventas, inventario, caja, turnos y nómina básica en una única plataforma rápida, sencilla, segura y accesible.

La solución combina un POS moderno con gestión operativa, funcionamiento offline y facturación electrónica, entregando valor inmediato en la primera versión y dejando una base tecnológica preparada para crecer, incorporar nuevos módulos y adaptarse a nuevas sedes.

NoSwitch propone a TuSisTiendas como una herramienta pensada para las necesidades reales de tiendas, quioscos y misceláneas en Colombia.

---

*Documento preparado por NoSwitch — TuSisTiendas — Versión 0.1 — 16 de agosto de 2026*

---

# ANEXO A — USO INTERNO NOSWITCH (NO ENVIAR AL CLIENTE)

## A.1 Cambios realizados

**Información interna eliminada:**

- Tabla de costos operativos desagregados (VPS Hostinger, dominio, correo, PostgreSQL, Redis, HTTPS/Caddy) y totales internos ($30.800 / $57.958). Se reemplazó por precio mensual único para el cliente.
- Fórmula "costo + 20% de ganancia" y tabla con cálculo ($30.800 × 1,20 / $57.958 × 1,20).
- Tabla de punto de equilibrio operativo y de recuperación de inversión, incluyendo "margen de ganancia mensual por cliente" ($6.160 / $11.592).
- Tabla de proyección de costos e ingresos a 3 años con "resultado neto" y análisis de rentabilidad de NoSwitch.
- Cualquier mención a "ganancia operativa", "margen", "recuperación del hardware por NoSwitch" y "punto de equilibrio de NoSwitch".

**Información comercial reorganizada:**

- Sección de presupuesto convertida en "Inversión y modelo de precios" con tabla única: hardware, implementación, mensualidad año 1 y mensualidad desde año 2.
- Detalle separado de "Qué incluye la inversión" y "Qué NO está incluido" para total claridad comercial.
- Lista de 50 requerimientos funcionales (RF-01 a RF-50) convertida en descripciones funcionales por módulo, en lenguaje para cliente.
- Requerimientos no funcionales técnicos fusionados en "Seguridad y respaldo", "Funcionamiento offline" y "Arquitectura y tecnología" con lenguaje simplificado.
- Arquitectura técnica completa conservada solo como resumen de confianza; se mantiene el detalle técnico como referencia en una línea.
- Estructura renumerada de 17 secciones internas a 22 secciones comerciales.
- **Cambio de alcance de hardware:** el paquete original de 3 terminales + 3 cajones + 3 lectores por $7.150.542 se redujo a solo 3 terminales 3nStar PTA0140 a $1.800.000 cada una ($5.400.000 total). Los cajones y lectores los aporta el cliente. Se añadió la posibilidad de cobros por domicilio.

**Inconsistencias encontradas:**

1. **Proyección anual desactualizada:** la tabla 14.6 anterior mostraba costos operativos anuales de $51.696 / $135.600 e ingresos de $62.040 / $162.720, valores que no corresponden a $30.800 × 12 = $369.600 ni a $36.960 × 12 = $443.520. Era un residuo del cálculo anterior al corregir el VPS a valores mensuales. Se eliminó la tabla completa en la versión comercial.
2. **Medios de pago inconsistentes:** la sección de alcance decía "(efectivo, transferencia, datáfono, pago múltiple)" mientras que ventas decía "(efectivo, tarjeta, Nequi, Daviplata, PSE y fiado)". Por indicación posterior se unificó en toda la propuesta a los medios reales del sistema: efectivo, transferencia, datáfono y pago mixto (con modal para registrar varios pagos a la vez), manteniendo la venta a fiado como opción de crédito descrita en su propia sección.
3. **Error tipográfico:** "funcionar de manera offline grâce a la tecnología PWA" (palabra francesa). Corregido a "gracias".
4. **Ambigüedad de nómina:** el resumen decía que lo fuera de alcance eran "funcionalidades avanzadas de nómina" sin definir el límite. Se aclaró: incluida = liquidación básica sobre turnos finalizados; no incluida = nómina avanzada (bonificaciones, deducciones complejas, prestaciones).
5. **Numeración:** la sección de mantenimiento aparecía como "14.4" dentro del capítulo 13. Corregido en la reorganización.
6. **Valor de implementación ($2.500.000):** se mantiene exactamente como estaba, pero sigue marcado como referencial hasta confirmación oficial.

## A.2 Aspectos que NoSwitch debe definir

Antes de enviar o firmar la propuesta, NoSwitch debe definir internamente (sin inventar respuestas en el documento comercial):

1. **Duración mínima del servicio:** ¿hay permanencia mínima de 12 meses o es mes a mes?
2. **Forma y fechas de pago:** medio de pago, día de corte, factura, intereses por mora.
3. **Transición año 1 → año 2:** cómo y cuándo se comunica el cambio de $36.960 a $69.550; ¿se firma desde ya o se renueva?
4. **Límites del soporte técnico básico:** qué incluye, horarios, canales, qué se cobra como soporte adicional.
5. **Tiempos de respuesta y garantía:** SLA ante fallos críticos, garantía del software y del hardware (¿cubre NoSwitch garantía de terminales o solo el fabricante?).
6. **Costos variables de terceros:** quién asume y cómo se cobra la facturación electrónica por documento, SMS, almacenamiento extra, comisiones de pago.
7. **Costo de funcionalidades futuras:** aclarar que sucursales, app nativa, contabilidad, etc. requieren cotización separada.
8. **Propiedad del software:** licencia de uso vs. propiedad; ¿qué ocurre con el acceso si el cliente termina el servicio?
9. **Propiedad y tratamiento de datos:** quién es dueño de los datos de ventas/inventario, cómo se exportan y eliminan al terminar, tratamiento de datos personales (Ley 1581 de 2012).
10. **Condiciones de terminación:** preaviso, entrega de información, estado del hardware ya pagado, copias de seguridad finales.
11. **Capacitación adicional:** cuántas sesiones incluye la implementación y costo de sesiones extra o por rotación de personal.
12. **Confirmar valores finales:** validar oficialmente $5.400.000 (hardware), $2.500.000 (implementación), $36.960 y $69.550 antes del envío.
13. **Cobro por domicilio:** definir si aplica, cómo se calcula (por distancia, transportadora, zona) y si se cotiza aparte o se incluye en el valor del hardware.
