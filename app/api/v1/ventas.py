from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError, PrinterError
from app.models.caja import SesionCaja
from app.models.configuracion import Configuracion
from app.models.producto import Producto
from app.models.sucursal import Cliente
from app.models.usuario import Usuario
from app.models.venta import MedioPago, Venta
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.venta import VentaCreate, VentaRead
from app.services.auth_service import get_current_user
from app.services.impresion_service import construir_lineas_tiquete, imprimir_ticket_doble
from app.services.venta_service import procesar_venta

router = APIRouter()


async def _cfg(db: AsyncSession, clave: str, default: str = "") -> str:
    result = await db.execute(select(Configuracion).where(Configuracion.clave == clave))
    config = result.scalar_one_or_none()
    return config.valor if config else default


@router.get("/medios")
async def list_medios_pago(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> list[dict]:
    from app.models.venta import MEDIOS_PAGO_VIGENTES

    result = await db.execute(
        select(MedioPago).where(
            MedioPago.activo.is_(True),
            MedioPago.tipo.in_(MEDIOS_PAGO_VIGENTES),
        )
    )
    medios = result.scalars().all()
    return [
        {
            "id_medio_pago": m.id_medio_pago,
            "nombre": m.nombre,
            "tipo": m.tipo.value,
            "requiere_referencia": m.requiere_referencia,
        }
        for m in medios
    ]


@router.get("/", response_model=None)
async def list_ventas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    id_sucursal: int | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> PaginatedResponse[VentaRead]:
    query = select(Venta).options(selectinload(Venta.detalles), selectinload(Venta.pagos))
    count_query = select(func.count()).select_from(Venta)

    filtros = []
    if id_sucursal:
        filtros.append(Venta.id_sucursal == id_sucursal)
    if fecha_desde:
        filtros.append(Venta.fecha_venta >= datetime.combine(fecha_desde, time.min))
    if fecha_hasta:
        filtros.append(Venta.fecha_venta <= datetime.combine(fecha_hasta, time.max))

    for filtro in filtros:
        query = query.where(filtro)
        count_query = count_query.where(filtro)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(Venta.fecha_venta.desc()))
    items = result.scalars().unique().all()

    return PaginatedResponse(
        items=[VentaRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/por-uuid/{uuid}", response_model=None)
async def get_venta_por_uuid(
    uuid: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> VentaRead:
    """Confirmación de sincronización: el dispositivo pregunta si su venta ya llegó."""
    result = await db.execute(
        select(Venta)
        .options(selectinload(Venta.detalles), selectinload(Venta.pagos))
        .where(Venta.uuid == uuid)
    )
    venta = result.scalar_one_or_none()
    if venta is None:
        raise NotFoundError("Venta", str(uuid))
    return VentaRead.model_validate(venta)


@router.post("/", response_model=None, status_code=201)
async def create_venta(
    body: VentaCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> VentaRead:
    venta = await procesar_venta(
        db,
        body,
        current_user.id_usuario,
        ip=request.client.host if request.client else None,
    )
    return VentaRead.model_validate(venta)


async def _datos_tiquete(db: AsyncSession, id_venta: int) -> tuple[list[str], list[str], int]:
    result = await db.execute(
        select(Venta)
        .options(selectinload(Venta.detalles), selectinload(Venta.pagos))
        .where(Venta.id_venta == id_venta)
    )
    venta = result.scalar_one_or_none()
    if venta is None:
        raise NotFoundError("Venta", id_venta)

    productos: dict[int, Producto] = {}
    if venta.detalles:
        prod_result = await db.execute(
            select(Producto).where(Producto.id_producto.in_([d.id_producto for d in venta.detalles]))
        )
        productos = {p.id_producto: p for p in prod_result.scalars().all()}

    medios_result = await db.execute(select(MedioPago))
    medios = {m.id_medio_pago: m for m in medios_result.scalars().all()}

    cajero = await db.get(Usuario, venta.id_usuario)
    cliente = None
    if venta.id_cliente:
        cliente = await db.get(Cliente, venta.id_cliente)
    sesion = await db.get(SesionCaja, venta.id_sesion_caja)

    negocio = {
        "nombre": await _cfg(db, "negocio.nombre", "TuSisTiendas"),
        "nit": await _cfg(db, "negocio.nit", ""),
        "direccion": await _cfg(db, "negocio.direccion", ""),
        "telefono": await _cfg(db, "negocio.telefono", ""),
        "mensaje": await _cfg(db, "ticket.mensaje", "Gracias por su compra"),
    }

    venta_data = {
        "consecutivo": venta.consecutivo,
        "fecha": venta.fecha_venta.strftime("%Y-%m-%d %H:%M"),
        "cajero": cajero.nombre_completo if cajero else "N/A",
        "cliente": cliente.nombre if cliente else "Consumidor final",
        "subtotal": float(venta.subtotal),
        "impuestos": float(venta.impuestos),
        "total": float(venta.total),
        "uuid": str(venta.uuid),
        "caja": sesion.id_punto_venta if sesion else None,
    }

    items = [
        {
            "nombre": productos[d.id_producto].nombre_producto if d.id_producto in productos else "Producto",
            "cantidad": float(d.cantidad),
            "precio": float(d.precio_unitario),
            "subtotal": float(d.subtotal) + float(d.subtotal) * float(d.iva_porcentaje) / 100,
        }
        for d in venta.detalles
    ]

    pagos = [
        {
            "metodo": medios[p.id_medio_pago].nombre if p.id_medio_pago in medios else "Pago",
            "monto": float(p.monto),
            "vuelto": float(p.vuelto or 0),
        }
        for p in venta.pagos
    ]

    copias = int(await _cfg(db, "ticket.copias", "2") or 2)
    return (
        construir_lineas_tiquete(negocio, venta_data, items, pagos, "CLIENTE"),
        construir_lineas_tiquete(negocio, venta_data, items, pagos, "COPIA NEGOCIO"),
        copias,
    )


@router.get("/{id_venta}/tiquete", response_model=None)
async def get_tiquete(
    id_venta: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    lineas_cliente, lineas_copia, copias = await _datos_tiquete(db, id_venta)
    return {"lineas_cliente": lineas_cliente, "lineas_copia": lineas_copia, "copias": copias}


@router.post("/{id_venta}/imprimir", response_model=None)
async def imprimir_venta(
    id_venta: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> MessageResponse:
    """Imprime el doble comprobante en la ticketera ESC/POS configurada."""
    lineas_cliente, lineas_copia, _copias = await _datos_tiquete(db, id_venta)
    try:
        imprimir_ticket_doble(lineas_cliente, lineas_copia)
    except PrinterError as exc:
        raise PrinterError(
            f"No se pudo imprimir en la ticketera configurada: {exc.message}. "
            "Use la impresión del navegador como respaldo."
        ) from exc
    return MessageResponse(message="Doble comprobante enviado a la ticketera")
