from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ConflictError, NotFoundError
from app.models.abono import AbonoCliente
from app.models.sucursal import Cliente
from app.models.usuario import Usuario
from app.models.venta import EstadoVenta, Venta
from app.schemas.cliente import AbonoCreate, AbonoRead, ClienteCreate, ClienteRead, ClienteUpdate, CuentaCliente
from app.schemas.common import PaginatedResponse
from app.services.auth_service import get_current_user
from app.services.cliente_service import calcular_saldo, registrar_abono

router = APIRouter()


def _sanitize(texto: str) -> str:
    return texto.replace("%", "").replace("_", "")


@router.get("/", response_model=None)
async def list_clientes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ClienteRead]:
    query = select(Cliente)
    count_query = select(func.count()).select_from(Cliente)

    if q:
        term = f"%{_sanitize(q)}%"
        like = or_(Cliente.nombre.ilike(term), Cliente.numero_doc.ilike(term), Cliente.telefono.ilike(term))
        query = query.where(like)
        count_query = count_query.where(like)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(Cliente.nombre))
    clientes = result.scalars().all()

    items = []
    for c in clientes:
        data = ClienteRead.model_validate(c)
        data.saldo_deudor = float(await calcular_saldo(db, c.id_cliente))
        items.append(data)

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=(total + page_size - 1) // page_size)


@router.post("/", response_model=None, status_code=201)
async def create_cliente(
    body: ClienteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ClienteRead:
    exists = await db.execute(select(Cliente).where(Cliente.numero_doc == body.numero_doc))
    if exists.scalar_one_or_none():
        raise ConflictError("Cliente con ese documento ya existe")

    cliente = Cliente(
        tipo_doc=body.tipo_doc,
        numero_doc=body.numero_doc,
        nombre=body.nombre,
        email=body.email,
        telefono=body.telefono,
        direccion=body.direccion,
        regimen_fiscal=body.regimen_fiscal,
    )
    db.add(cliente)
    await db.flush()
    return ClienteRead.model_validate(cliente)


@router.get("/buscar", response_model=None)
async def buscar_clientes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    q: str,
) -> list[ClienteRead]:
    term = f"%{_sanitize(q)}%"
    result = await db.execute(
        select(Cliente)
        .where(or_(Cliente.nombre.ilike(term), Cliente.numero_doc.ilike(term), Cliente.telefono.ilike(term)))
        .limit(20)
    )
    clientes = result.scalars().all()
    return [ClienteRead.model_validate(c) for c in clientes]


@router.get("/{id_cliente}", response_model=None)
async def get_cliente(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ClienteRead:
    cliente = await db.get(Cliente, id_cliente)
    if not cliente:
        raise NotFoundError("Cliente", id_cliente)
    data = ClienteRead.model_validate(cliente)
    data.saldo_deudor = float(await calcular_saldo(db, id_cliente))
    return data


@router.put("/{id_cliente}", response_model=None)
async def update_cliente(
    id_cliente: int,
    body: ClienteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ClienteRead:
    cliente = await db.get(Cliente, id_cliente)
    if not cliente:
        raise NotFoundError("Cliente", id_cliente)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    return ClienteRead.model_validate(cliente)


@router.get("/{id_cliente}/cuenta", response_model=None)
async def get_cuenta_cliente(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> CuentaCliente:
    cliente = await db.get(Cliente, id_cliente)
    if not cliente:
        raise NotFoundError("Cliente", id_cliente)

    result_ventas = await db.execute(
        select(Venta).where(Venta.id_cliente == id_cliente, Venta.estado == EstadoVenta.pendiente)
    )
    ventas_pend = result_ventas.scalars().all()

    result_abonos = await db.execute(
        select(AbonoCliente).where(AbonoCliente.id_cliente == id_cliente).order_by(AbonoCliente.fecha.desc())
    )
    abonos = result_abonos.scalars().all()

    return CuentaCliente(
        id_cliente=id_cliente,
        nombre=cliente.nombre,
        saldo_deudor=float(await calcular_saldo(db, id_cliente)),
        ventas_pendientes=[
            {
                "id_venta": v.id_venta,
                "fecha": v.fecha_venta,
                "total": float(v.total),
                "monto_abonado": float(v.monto_abonado),
                "monto_devuelto": float(v.monto_devuelto),
            }
            for v in ventas_pend
        ],
        abonos=[AbonoRead.model_validate(a) for a in abonos],
    )


@router.post("/abonos", response_model=None, status_code=201)
async def create_abono(
    body: AbonoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> AbonoRead:
    abono = await registrar_abono(
        db,
        id_cliente=body.id_cliente,
        id_venta=body.id_venta,
        monto=body.monto,
        id_usuario=current_user.id_usuario,
        observacion=body.observacion,
    )
    return AbonoRead.model_validate(abono)