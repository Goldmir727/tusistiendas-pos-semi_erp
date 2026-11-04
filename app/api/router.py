from fastapi import APIRouter

from app.api.v1 import (
    auth,
    usuarios,
    productos,
    turnos,
    caja,
    ventas,
    pagos,
    comprobantes,
    reportes,
    configuracion,
    clientes,
    compras,
    devoluciones,
    egresos,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
api_router.include_router(productos.router, prefix="/productos", tags=["Productos"])
api_router.include_router(turnos.router, prefix="/turnos", tags=["Turnos"])
api_router.include_router(caja.router, prefix="/caja", tags=["Caja"])
api_router.include_router(ventas.router, prefix="/ventas", tags=["Ventas"])
api_router.include_router(pagos.router, prefix="/pagos", tags=["Pagos Sueldos"])
api_router.include_router(comprobantes.router, prefix="/comprobantes", tags=["Comprobantes DIAN"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])
api_router.include_router(configuracion.router, prefix="/configuracion", tags=["Configuracion"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(compras.router, prefix="/compras", tags=["Compras"])
api_router.include_router(devoluciones.router, prefix="/devoluciones", tags=["Devoluciones"])
api_router.include_router(egresos.router, prefix="/egresos", tags=["Egresos"])
