from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.config import get_settings
from app.database import Base, async_session_factory, engine
from app.models.caja import SesionCaja
from app.models.configuracion import Configuracion
from app.models.compra import Proveedor
from app.models.pago import MetodoPagoSueldo, PagoSueldo, PagoTurnoDetalle
from app.models.sucursal import Cliente, PuntoVenta, Sucursal
from app.models.turno import EstadoTurno, TarifaTurno, TurnoCalendario, TurnoPlantilla
from app.models.usuario import Permiso, RolEnum, Usuario
from app.models.venta import MedioPago, MetodoPago
from app.services.auth_service import hash_contrasena
from app.services.turno_service import duracion_horas, hoy_local

TZ = ZoneInfo(get_settings().TIMEZONE)


PERMISOS = [
    ("caja.abrir", "Abrir sesion de caja"),
    ("caja.cerrar", "Cerrar sesion de caja"),
    ("caja.ver_panel", "Ver panel doble de caja"),
    ("ventas.crear", "Crear ventas"),
    ("ventas.ver", "Ver ventas"),
    ("productos.crear", "Crear productos"),
    ("productos.editar", "Editar productos"),
    ("productos.ver", "Ver productos"),
    ("turnos.crear", "Crear turnos"),
    ("turnos.aprobar_reemplazo", "Aprobar reemplazos"),
    ("turnos.ver", "Ver turnos"),
    ("pagos.crear", "Crear pagos de sueldo"),
    ("pagos.ver", "Ver pagos de sueldo"),
    ("reportes.ver", "Ver reportes"),
    ("configuracion.editar", "Editar configuracion"),
    ("usuarios.crear", "Crear usuarios"),
    ("usuarios.editar", "Editar usuarios"),
    ("usuarios.ver", "Ver usuarios"),
    ("clientes.crear", "Crear clientes"),
    ("clientes.ver", "Ver clientes"),
    ("clientes.abono", "Registrar abonos de fiado"),
    ("compras.registrar", "Registrar compras"),
    ("compras.ver", "Ver compras"),
    ("devoluciones.crear", "Crear devoluciones"),
    ("devoluciones.aprobar", "Aprobar devoluciones"),
    ("egresos.registrar", "Registrar egresos"),
    ("egresos.ver", "Ver egresos"),
]

CONFIGURACION_DEFAULT = [
    ("negocio.nombre", "TuSisTiendas", "string", "Nombre del negocio en los tiquetes"),
    ("negocio.nit", "", "string", "NIT del negocio"),
    ("negocio.direccion", "", "string", "Direccion del negocio"),
    ("negocio.telefono", "", "string", "Telefono del negocio"),
    ("ticket.mensaje", "Gracias por su compra", "string", "Mensaje al pie del tiquete"),
    ("ticket.copias", "2", "number", "Copias del tiquete: original y copia"),
    ("productos.margen_ganancia_default", "30", "number", "Porcentaje de ganancia default al crear productos (0 = desactivado)"),
    ("turnos.hora_inicio", "6", "number", "Hora de inicio del calendario de turnos (0-23)"),
    ("turnos.hora_fin", "24", "number", "Hora de fin del calendario de turnos (0-24)"),
    ("devoluciones.max_por_turno_cajero", "50000", "number", "Monto maximo de devoluciones auto-aprobadas por cajero en el turno"),
    ("caja.requiere_turno_activo", "1", "boolean", "Exigir turno activo para abrir caja (1 = si)"),
]

MEDIOS_PAGO_DEFAULT = [
    ("Efectivo", MetodoPago.efectivo, False),
    ("Transferencia", MetodoPago.transferencia, True),
    ("Datafono", MetodoPago.datafono, True),
    ("Fiado", MetodoPago.fiado, False),
]

TIPOS_HEREDADOS = {"tarjeta", "nequi", "daviplata", "pse"}

# Horarios y valores segun la tabla adjunta (fila mas cercana cuando no coincide exacto).
TURNOS_PATRON = {
    "morning_6_15": ("06:00", "15:00", 63000),
    "morning_7_15": ("07:00", "15:00", 54000),
    "afternoon_15_23": ("15:00", "23:00", 54000),
    "afternoon_15_00": ("15:00", "00:00", 56000),
    "afternoon_16_00": ("16:00", "00:00", 56000),
    "friday_17_01": ("17:00", "01:00", 71000),
    "sunday_16_01": ("16:00", "01:00", 73000),
}

# Valores de prueba. En producción el administrador puede crear, editar y
# desactivar estas reglas desde el módulo de Turnos.
TARIFAS_DEFAULT = [
    ("Mañana 06:00 a 15:00", "06:00", "15:00", list(range(7)), 63000, 0),
    ("Mañana 07:00 a 15:00", "07:00", "15:00", list(range(7)), 54000, 0),
    ("Tarde 15:00 a 23:00", "15:00", "23:00", list(range(7)), 54000, 0),
    ("Tarde 15:00 a 00:00", "15:00", "00:00", list(range(7)), 56000, 0),
    ("Tarde 16:00 a 00:00", "16:00", "00:00", list(range(7)), 56000, 0),
    ("Viernes noche 17:00 a 01:00", "17:00", "01:00", [4], 71000, 10),
    ("Domingo noche 16:00 a 01:00", "16:00", "01:00", [6], 73000, 10),
]

# Empleados: (nombre, email, sucursal, patron, dias_semana ISO: Monday=0..Sunday=6)
EMPLEADOS = [
    ("Ana Maria Rodriguez", "empleado01@pos.com", "Tienda Principal", "morning_6_15", [0, 1, 2, 5]),
    ("Carlos Andres Gomez", "empleado02@pos.com", "Tienda Principal", "morning_7_15", [0, 1, 2, 3, 4]),
    ("Laura Valentina Martinez", "empleado03@pos.com", "Tienda Principal", "afternoon_15_23", [0, 1, 2, 4, 5]),
    ("Juan Sebastian Perez", "empleado04@pos.com", "Tienda Principal", "afternoon_16_00", [0, 1, 2, 3, 6]),
    ("Camila Andrea Torres", "empleado05@pos.com", "Sucursal Norte", "morning_6_15", [0, 1, 3, 5]),
    ("Andres Felipe Ramirez", "empleado06@pos.com", "Sucursal Norte", "morning_7_15", [0, 1, 2, 4, 5]),
    ("Valentina Lopez", "empleado07@pos.com", "Sucursal Norte", "afternoon_15_00", [1, 2, 3, 5]),
    ("Santiago Herrera", "empleado08@pos.com", "Sucursal Norte", "afternoon_16_00", [0, 1, 2, 4, 6]),
    ("Daniela Castillo", "empleado09@pos.com", "Sucursal Sur", "afternoon_15_23", [0, 1, 2, 4, 5]),
    ("Miguel Angel Vargas", "empleado10@pos.com", "Sucursal Sur", "afternoon_16_00", [0, 1, 2, 3, 4]),
    ("Sofia Jimenez", "empleado11@pos.com", "Sucursal Sur", "afternoon_15_23", [0, 1, 2, 3, 6]),
]

# Reemplazos: (titular_email, reemplazo_email, semana_offset, patron, dia_semana, estado)
REEMPLAZOS = [
    ("empleado03@pos.com", "empleado04@pos.com", -2, "afternoon_15_23", 5, EstadoTurno.pagado),
    ("empleado07@pos.com", None, 1, "afternoon_15_00", 5, EstadoTurno.solicitud_reemplazo),
    ("empleado09@pos.com", "empleado11@pos.com", 1, "afternoon_15_23", 5, EstadoTurno.reemplazo_pendiente_aprobacion),
]


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _dias_patron(plantilla: TurnoPlantilla) -> list[int]:
    if plantilla.dias_semana:
        return sorted({int(d) for d in plantilla.dias_semana})
    if plantilla.dia_semana is not None:
        return [int(plantilla.dia_semana)]
    return []


async def _get_or_create_sucursal(db, nombre, direccion, telefono):
    suc = (await db.execute(select(Sucursal).where(Sucursal.nombre == nombre))).scalar_one_or_none()
    if suc is None:
        suc = Sucursal(nombre=nombre, direccion=direccion, telefono=telefono, activa=True)
        db.add(suc)
        await db.flush()
    return suc


async def _get_or_create_punto(db, id_sucursal, nombre, impresora):
    pv = (await db.execute(
        select(PuntoVenta).where(PuntoVenta.nombre == nombre, PuntoVenta.id_sucursal == id_sucursal)
    )).scalar_one_or_none()
    if pv is None:
        pv = PuntoVenta(id_sucursal=id_sucursal, nombre=nombre, impresora_ticketera=impresora, activa=True)
        db.add(pv)
        await db.flush()
    return pv


async def _get_or_create_usuario(db, email, defaults):
    u = (await db.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
    if u is None:
        u = Usuario(**defaults)
        db.add(u)
        await db.flush()
    else:
        # Asegurar asignacion de sucursal/punto sin sobrescribir cambios manuales
        if u.id_sucursal is None and defaults.get("id_sucursal") is not None:
            u.id_sucursal = defaults["id_sucursal"]
        if u.id_punto_venta is None and defaults.get("id_punto_venta") is not None:
            u.id_punto_venta = defaults["id_punto_venta"]
    return u


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Sucursales
        suc_centro = await _get_or_create_sucursal(db, "Tienda Principal", "Calle 123 #45-67", "3001234567")
        suc_norte = await _get_or_create_sucursal(db, "Sucursal Norte", "Carrera 10 #20-30", "3002223333")
        suc_sur = await _get_or_create_sucursal(db, "Sucursal Sur", "Avenida 5 #12-45", "3004445555")
        sucursales = {"Tienda Principal": suc_centro, "Sucursal Norte": suc_norte, "Sucursal Sur": suc_sur}

        # Cajas
        cajas = {}
        for suc in (suc_centro, suc_norte, suc_sur):
            cantidad = 3 if suc.id_sucursal == suc_centro.id_sucursal else 2
            for n in range(1, cantidad + 1):
                pv = await _get_or_create_punto(db, suc.id_sucursal, f"Caja {n}", f"PTA0140-{n}")
                cajas[(suc.nombre, n)] = pv

        # Permisos
        for codigo, descripcion in PERMISOS:
            existe = (await db.execute(select(Permiso).where(Permiso.codigo == codigo))).scalar_one_or_none()
            if existe is None:
                db.add(Permiso(codigo=codigo, descripcion=descripcion))

        # Configuracion
        for clave, valor, tipo, descripcion in CONFIGURACION_DEFAULT:
            existe = (await db.execute(select(Configuracion).where(Configuracion.clave == clave))).scalar_one_or_none()
            if existe is None:
                db.add(Configuracion(clave=clave, valor=valor, tipo=tipo, descripcion=descripcion))
            elif clave == "turnos.hora_fin" and existe.valor in ("22", "23"):
                existe.valor = "24"

        # Tarifas de turno (reglas de ejemplo, editables desde la interfaz)
        for nombre, ini, fin, dias, valor, prioridad in TARIFAS_DEFAULT:
            existe = (
                await db.execute(select(TarifaTurno).where(TarifaTurno.nombre == nombre))
            ).scalar_one_or_none()
            if existe is None:
                db.add(
                    TarifaTurno(
                        nombre=nombre,
                        hora_inicio=_t(ini),
                        hora_fin=_t(fin),
                        dias_semana=dias,
                        valor=valor,
                        prioridad=prioridad,
                        activa=True,
                    )
                )

        # Medios de pago
        for nombre, tipo, requiere_referencia in MEDIOS_PAGO_DEFAULT:
            existe = (await db.execute(select(MedioPago).where(MedioPago.tipo == tipo))).scalar_one_or_none()
            if existe is None:
                db.add(MedioPago(nombre=nombre, tipo=tipo, comision_porcentaje=0, requiere_qr=False, requiere_referencia=requiere_referencia, activo=True))
            elif not existe.activo:
                existe.activo = True

        heredados = [
            m for m in (await db.execute(select(MedioPago))).scalars().all()
            if m.tipo.value in TIPOS_HEREDADOS and m.activo
        ]
        for medio in heredados:
            medio.activo = False

        # Proveedor y cliente demo
        if not (await db.execute(select(Proveedor).where(Proveedor.nit == "900123456-1"))).scalar_one_or_none():
            db.add(Proveedor(nombre="Distribuidora Demo SAS", nit="900123456-1", telefono="3001112222", email="ventas@demodist.com", direccion="Calle 10 #20-30", activo=True))
        if not (await db.execute(select(Cliente).where(Cliente.numero_doc == "1234567890"))).scalar_one_or_none():
            db.add(Cliente(tipo_doc="CC", numero_doc="1234567890", nombre="Cliente Fiado Demo", email="fiado@demo.com", telefono="3109998888", direccion="Carrera 5 #12-45", regimen_fiscal="regimen_simplificado", activo=True))

        # Admin
        admin = (await db.execute(select(Usuario).where(Usuario.email == "admin@pos.com"))).scalar_one_or_none()
        if admin is None:
            admin = Usuario(
                nombre_completo="Administrador Principal",
                email="admin@pos.com",
                documento_identidad="1000000000",
                contrasena_hash=hash_contrasena("admin123"),
                rol=RolEnum.administrador,
                activo=True,
                id_sucursal=suc_centro.id_sucursal,
            )
            db.add(admin)
            await db.flush()

        # Legacy cajero
        cajero_legacy = (await db.execute(select(Usuario).where(Usuario.email == "cajero@pos.com"))).scalar_one_or_none()
        if cajero_legacy is None:
            cajero_legacy = Usuario(
                nombre_completo="Cajero Demo",
                email="cajero@pos.com",
                documento_identidad="1000000001",
                contrasena_hash=hash_contrasena("cajero123"),
                rol=RolEnum.cajero,
                activo=True,
                id_sucursal=suc_centro.id_sucursal,
                id_punto_venta=cajas[("Tienda Principal", 2)].id_punto_venta,
            )
            db.add(cajero_legacy)
            await db.flush()
        else:
            if cajero_legacy.id_punto_venta is None:
                cajero_legacy.id_punto_venta = cajas[("Tienda Principal", 2)].id_punto_venta

        # 3 cuentas de caja de prueba
        caja_accounts = [
            ("caja.principal@pos.com", "Cajero Tienda Principal", "3000000001", "Tienda Principal", 1),
            ("caja.norte@pos.com", "Cajero Sucursal Norte", "3000000002", "Sucursal Norte", 1),
            ("caja.sur@pos.com", "Cajero Sucursal Sur", "3000000003", "Sucursal Sur", 1),
        ]
        caja_users = {}
        for email, nombre, doc, suc_nombre, caja_num in caja_accounts:
            suc = sucursales[suc_nombre]
            pv = cajas[(suc_nombre, caja_num)]
            u = await _get_or_create_usuario(db, email, {
                "nombre_completo": nombre,
                "email": email,
                "documento_identidad": doc,
                "contrasena_hash": hash_contrasena("caja123"),
                "rol": RolEnum.cajero,
                "activo": True,
                "id_sucursal": suc.id_sucursal,
                "id_punto_venta": pv.id_punto_venta,
                "telefono": "3100000000",
                "banco_nombre": "Bancolombia",
                "banco_numero_cuenta": doc,
            })
            caja_users[email] = u

        # 11 empleados
        empleados = []
        for i, (nombre, email, suc_nombre, patron, dias) in enumerate(EMPLEADOS, start=1):
            suc = sucursales[suc_nombre]
            doc = f"20000000{i:02d}"
            u = await _get_or_create_usuario(db, email, {
                "nombre_completo": nombre,
                "email": email,
                "documento_identidad": doc,
                "contrasena_hash": hash_contrasena("empleado123"),
                "rol": RolEnum.empleado,
                "activo": True,
                "id_sucursal": suc.id_sucursal,
                "telefono": f"3200000{i:04d}",
                "banco_nombre": "Bancolombia" if i % 2 else "Davivienda",
                "banco_numero_cuenta": f"0000{i:06d}",
            })
            empleados.append((u, suc, patron, dias))

        # Patrones semanales reutilizables para generar meses completos.
        for u, suc, patron, dias in empleados:
            ini, fin, valor = TURNOS_PATRON[patron]
            hi, hf = _t(ini), _t(fin)
            existentes = (
                await db.execute(
                    select(TurnoPlantilla).where(
                        TurnoPlantilla.id_usuario_titular == u.id_usuario
                    )
                )
            ).scalars().all()
            coincide = next(
                (
                    p
                    for p in existentes
                    if _dias_patron(p) == sorted(dias)
                    and p.hora_inicio == hi
                    and p.hora_fin == hf
                ),
                None,
            )
            if coincide is None:
                db.add(
                    TurnoPlantilla(
                        nombre=f"Patrón semanal {u.nombre_completo}",
                        dia_semana=dias[0],
                        dias_semana=sorted(dias),
                        hora_inicio=hi,
                        hora_fin=hf,
                        valor_total_turno=valor,
                        usar_tarifa=True,
                        id_usuario_titular=u.id_usuario,
                        id_sucursal=suc.id_sucursal,
                        activa=True,
                    )
                )

        await db.commit()

        # Turnos: 5 semanas
        hoy = hoy_local()
        semana_actual = _week_start(hoy)
        semanas = [semana_actual + timedelta(weeks=w) for w in range(-3, 2)]

        turnos_creados = 0
        turnos_por_empleado_semana = {}  # (user_id, week_start) -> list of TurnoCalendario

        for u, suc, patron, dias in empleados:
            ini, fin, valor = TURNOS_PATRON[patron]
            hi, hf = _t(ini), _t(fin)
            for ws in semanas:
                for offset in range(7):
                    fecha = ws + timedelta(days=offset)
                    if fecha.weekday() not in dias:
                        continue
                    # No generar turnos futuros mas alla de +1 semana (ya incluido)
                    existing = (await db.execute(
                        select(TurnoCalendario).where(
                            TurnoCalendario.id_usuario_titular == u.id_usuario,
                            TurnoCalendario.fecha == fecha,
                            TurnoCalendario.hora_inicio == hi,
                            TurnoCalendario.hora_fin == hf,
                        )
                    )).scalar_one_or_none()
                    if existing is not None:
                        turno = existing
                    else:
                        turno = TurnoCalendario(
                            id_usuario_titular=u.id_usuario,
                            fecha=fecha,
                            hora_inicio=hi,
                            hora_fin=hf,
                            valor_total_turno=valor,
                            id_sucursal=suc.id_sucursal,
                        )
                        db.add(turno)
                        await db.flush()
                        turnos_creados += 1

                    # Estado segun fecha
                    if fecha < hoy:
                        if turno.estado_turno not in (EstadoTurno.pagado,):
                            turno.estado_turno = EstadoTurno.finalizado
                    elif fecha == hoy:
                        if turno.estado_turno == EstadoTurno.programado:
                            pass
                    else:
                        if turno.estado_turno not in (EstadoTurno.solicitud_reemplazo, EstadoTurno.reemplazo_pendiente_aprobacion):
                            turno.estado_turno = EstadoTurno.programado

                    # Hora real para pasados
                    if fecha < hoy and turno.hora_apertura_real is None:
                        apertura = datetime.combine(fecha, hi, tzinfo=TZ) + timedelta(minutes=5)
                        cierre = datetime.combine(fecha, hf, tzinfo=TZ)
                        if hf <= hi:
                            cierre = cierre + timedelta(days=1)
                        cierre = cierre + timedelta(minutes=10)
                        turno.hora_apertura_real = apertura.replace(tzinfo=None)
                        turno.hora_cierre_real = cierre.replace(tzinfo=None)

                    turnos_por_empleado_semana.setdefault((u.id_usuario, ws), []).append(turno)

        await db.commit()

        # Reemplazos
        for titular_email, reemplazo_email, week_offset, patron, dia, estado in REEMPLAZOS:
            titular = (await db.execute(select(Usuario).where(Usuario.email == titular_email))).scalar_one()
            reemplazo = None
            if reemplazo_email:
                reemplazo = (await db.execute(select(Usuario).where(Usuario.email == reemplazo_email))).scalar_one()
            suc = sucursales[[e[2] for e in EMPLEADOS if e[1] == titular_email][0]]
            ws = semana_actual + timedelta(weeks=week_offset)
            fecha = ws + timedelta(days=dia - ws.weekday() if False else 0)
            # calcular fecha del dia de la semana dentro de esa semana
            fecha = ws + timedelta(days=(dia - 0))  # placeholder, se corrige abajo
            # dia es 0..6 (lunes..domingo) en terminos de weekday()
            fecha = ws + timedelta(days=dia)
            ini, fin, valor = TURNOS_PATRON[patron]
            hi, hf = _t(ini), _t(fin)
            turno = (await db.execute(
                select(TurnoCalendario).where(
                    TurnoCalendario.id_usuario_titular == titular.id_usuario,
                    TurnoCalendario.fecha == fecha,
                    TurnoCalendario.hora_inicio == hi,
                    TurnoCalendario.hora_fin == hf,
                )
            )).scalar_one_or_none()
            if turno is None:
                turno = TurnoCalendario(
                    id_usuario_titular=titular.id_usuario,
                    fecha=fecha,
                    hora_inicio=hi,
                    hora_fin=hf,
                    valor_total_turno=valor,
                    id_sucursal=suc.id_sucursal,
                )
                db.add(turno)
                await db.flush()
            if reemplazo is not None:
                turno.id_usuario_reemplazo = reemplazo.id_usuario
            turno.horas_reemplazadas_parcial = 0
            turno.estado_turno = estado
            # Si es pagado, marcar real times
            if fecha < hoy and turno.hora_apertura_real is None:
                apertura = datetime.combine(fecha, hi, tzinfo=TZ) + timedelta(minutes=5)
                cierre = datetime.combine(fecha, hf, tzinfo=TZ)
                if hf <= hi:
                    cierre = cierre + timedelta(days=1)
                cierre = cierre + timedelta(minutes=10)
                turno.hora_apertura_real = apertura.replace(tzinfo=None)
                turno.hora_cierre_real = cierre.replace(tzinfo=None)

        await db.commit()

        # Pagos: semanas -3, -2 y -1 (parcial)
        admin = (await db.execute(select(Usuario).where(Usuario.email == "admin@pos.com"))).scalar_one()
        pagos_creados = 0
        for week_offset in (-3, -2, -1):
            ws = semana_actual + timedelta(weeks=week_offset)
            semana_fin = ws + timedelta(days=5)
            fecha_pago = datetime.combine(semana_fin, time(18, 0))
            solo_empleados = None
            if week_offset == -1:
                solo_empleados = {f"empleado{i:02d}@pos.com" for i in range(1, 7)}

            for u, suc, patron, dias in empleados:
                if solo_empleados is not None and u.email not in solo_empleados:
                    continue
                # Recoger turnos finalizados/pagados de esa semana donde el beneficiario es el empleado
                turnos_semana = (await db.execute(
                    select(TurnoCalendario).where(
                        TurnoCalendario.fecha >= ws,
                        TurnoCalendario.fecha <= ws + timedelta(days=6),
                        (TurnoCalendario.id_usuario_titular == u.id_usuario)
                        | (TurnoCalendario.id_usuario_reemplazo == u.id_usuario),
                    )
                )).scalars().all()

                turnos_a_pagar = []
                for t in turnos_semana:
                    from app.services.turno_service import beneficiario_turno as bt
                    if bt(t) != u.id_usuario:
                        continue
                    # Excluir si ya tiene detalle de pago
                    existe_detalle = (await db.execute(
                        select(PagoTurnoDetalle).where(PagoTurnoDetalle.id_turno == t.id_turno)
                    )).scalar_one_or_none()
                    if existe_detalle is not None:
                        continue
                    turnos_a_pagar.append(t)

                if not turnos_a_pagar:
                    continue

                observacion = f"seed:{ws.isoformat()}:{u.id_usuario}"
                pago_existente = (await db.execute(
                    select(PagoSueldo).where(PagoSueldo.observacion == observacion)
                )).scalar_one_or_none()
                if pago_existente is not None:
                    continue

                monto_total = sum(float(t.valor_total_turno) for t in turnos_a_pagar)
                if week_offset == -2 and u.id_usuario % 2 == 0:
                    recibido = False
                elif week_offset == -3:
                    recibido = True
                else:
                    recibido = False

                metodo = MetodoPagoSueldo.transferencia if u.id_usuario % 2 == 0 else MetodoPagoSueldo.efectivo
                pago = PagoSueldo(
                    id_usuario_receptor=u.id_usuario,
                    id_administrador_pagador=admin.id_usuario,
                    fecha_pago=fecha_pago,
                    metodo_pago=metodo,
                    monto_total=monto_total,
                    observacion=observacion,
                    recibido_empleado=recibido,
                    fecha_recibido=fecha_pago + timedelta(days=1) if recibido else None,
                )
                db.add(pago)
                await db.flush()

                for t in turnos_a_pagar:
                    db.add(PagoTurnoDetalle(
                        id_pago=pago.id_pago,
                        id_turno=t.id_turno,
                        monto_liquidado_turno=float(t.valor_total_turno),
                    ))
                    t.estado_turno = EstadoTurno.pagado

                pagos_creados += 1

        await db.commit()

        print("Seed completado (sin borrar datos existentes):")
        print(f"  Sucursales: Tienda Principal, Sucursal Norte, Sucursal Sur")
        print(f"  Cajas: {len(cajas)}")
        print(f"  Cuentas de caja: 3 (caja123) + legacy cajero@pos.com")
        print(f"  Empleados: {len(empleados)} (empleado123)")
        print(f"  Turnos creados: {turnos_creados}")
        print(f"  Pagos creados: {pagos_creados}")
        print(f"  Admin: admin@pos.com / admin123")


if __name__ == "__main__":
    asyncio.run(seed())