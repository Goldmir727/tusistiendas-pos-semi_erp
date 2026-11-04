from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import Base, async_session_factory, engine
from app.models.configuracion import Configuracion
from app.models.compra import Proveedor
from app.models.sucursal import Cliente, PuntoVenta, Sucursal
from app.models.usuario import Permiso, RolEnum, Usuario
from app.models.venta import MedioPago, MetodoPago
from app.services.auth_service import hash_contrasena


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
    ("turnos.hora_fin", "22", "number", "Hora de fin del calendario de turnos (0-23)"),
    ("devoluciones.max_por_turno_cajero", "50000", "number", "Monto maximo de devoluciones auto-aprobadas por cajero en el turno"),
    ("caja.requiere_turno_activo", "0", "boolean", "Exigir turno activo para abrir caja (1 = si)"),
]

MEDIOS_PAGO_DEFAULT = [
    ("Efectivo", MetodoPago.efectivo, False),
    ("Transferencia", MetodoPago.transferencia, True),
    ("Datafono", MetodoPago.datafono, True),
    ("Fiado", MetodoPago.fiado, False),
]

TIPOS_HEREDADOS = {"tarjeta", "nequi", "daviplata", "pse"}


async def seed() -> None:
    async with engine.begin() as conn:
        # Sin drop_all: el seed nunca borra informacion del negocio.
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        sucursal = (
            await db.execute(select(Sucursal).where(Sucursal.nombre == "Tienda Principal"))
        ).scalar_one_or_none()
        if sucursal is None:
            sucursal = Sucursal(
                nombre="Tienda Principal",
                direccion="Calle 123 #45-67",
                telefono="3001234567",
                activa=True,
            )
            db.add(sucursal)
            await db.flush()

        cajas_creadas = 0
        for numero in range(1, 4):
            nombre = f"Caja {numero}"
            existe = (
                await db.execute(
                    select(PuntoVenta).where(
                        PuntoVenta.nombre == nombre,
                        PuntoVenta.id_sucursal == sucursal.id_sucursal,
                    )
                )
            ).scalar_one_or_none()
            if existe is None:
                db.add(
                    PuntoVenta(
                        id_sucursal=sucursal.id_sucursal,
                        nombre=nombre,
                        impresora_ticketera=f"PTA0140-{numero}",
                        activa=True,
                    )
                )
                cajas_creadas += 1

        permisos_creados = 0
        for codigo, descripcion in PERMISOS:
            existe = (await db.execute(select(Permiso).where(Permiso.codigo == codigo))).scalar_one_or_none()
            if existe is None:
                db.add(Permiso(codigo=codigo, descripcion=descripcion))
                permisos_creados += 1

        config_creadas = 0
        for clave, valor, tipo, descripcion in CONFIGURACION_DEFAULT:
            existe = (await db.execute(select(Configuracion).where(Configuracion.clave == clave))).scalar_one_or_none()
            if existe is None:
                db.add(Configuracion(clave=clave, valor=valor, tipo=tipo, descripcion=descripcion))
                config_creadas += 1

        medios_creados = 0
        for nombre, tipo, requiere_referencia in MEDIOS_PAGO_DEFAULT:
            existe = (await db.execute(select(MedioPago).where(MedioPago.tipo == tipo))).scalar_one_or_none()
            if existe is None:
                db.add(
                    MedioPago(
                        nombre=nombre,
                        tipo=tipo,
                        comision_porcentaje=0,
                        requiere_qr=False,
                        requiere_referencia=requiere_referencia,
                        activo=True,
                    )
                )
                medios_creados += 1
            elif not existe.activo:
                existe.activo = True

        # Los medios heredados dejan de ofrecerse en caja.
        heredados = [
            m
            for m in (await db.execute(select(MedioPago))).scalars().all()
            if m.tipo.value in TIPOS_HEREDADOS and m.activo
        ]
        for medio in heredados:
            medio.activo = False

        if not (await db.execute(select(Proveedor).where(Proveedor.nit == "900123456-1"))).scalar_one_or_none():
            db.add(
                Proveedor(
                    nombre="Distribuidora Demo SAS",
                    nit="900123456-1",
                    telefono="3001112222",
                    email="ventas@demodist.com",
                    direccion="Calle 10 #20-30",
                    activo=True,
                )
            )

        if not (await db.execute(select(Cliente).where(Cliente.numero_doc == "1234567890"))).scalar_one_or_none():
            db.add(
                Cliente(
                    tipo_doc="CC",
                    numero_doc="1234567890",
                    nombre="Cliente Fiado Demo",
                    email="fiado@demo.com",
                    telefono="3109998888",
                    direccion="Carrera 5 #12-45",
                    regimen_fiscal="regimen_simplificado",
                    activo=True,
                )
            )

        admin = (await db.execute(select(Usuario).where(Usuario.email == "admin@pos.com"))).scalar_one_or_none()
        if admin is None:
            db.add(
                Usuario(
                    nombre_completo="Administrador Principal",
                    email="admin@pos.com",
                    documento_identidad="1000000000",
                    contrasena_hash=hash_contrasena("admin123"),
                    rol=RolEnum.administrador,
                    activo=True,
                    id_sucursal=sucursal.id_sucursal,
                )
            )

        cajero = (await db.execute(select(Usuario).where(Usuario.email == "cajero@pos.com"))).scalar_one_or_none()
        if cajero is None:
            db.add(
                Usuario(
                    nombre_completo="Cajero Demo",
                    email="cajero@pos.com",
                    documento_identidad="1000000001",
                    contrasena_hash=hash_contrasena("cajero123"),
                    rol=RolEnum.cajero,
                    activo=True,
                    id_sucursal=sucursal.id_sucursal,
                )
            )

        await db.commit()

        print("Seed completado (sin borrar datos existentes):")
        print(f"  Sucursal: {sucursal.nombre} (ID {sucursal.id_sucursal})")
        print(f"  Cajas nuevas: {cajas_creadas}")
        print(f"  Admin: admin@pos.com / admin123")
        print(f"  Cajero: cajero@pos.com / cajero123")
        print(f"  Permisos nuevos: {permisos_creados}")
        print(f"  Configuraciones nuevas: {config_creadas}")
        print(f"  Medios de pago nuevos: {medios_creados}")
        print(f"  Medios heredados desactivados: {len(heredados)}")


if __name__ == "__main__":
    asyncio.run(seed())
