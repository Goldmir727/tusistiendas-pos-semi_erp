"""Carga el catálogo extraído de TiendasON en la base.

El CSV viene del extractor: separador ';', decimales con coma y punto de miles
(666,67). Las categorías del archivo no se guardan porque el modelo Producto
todavía no tiene ese campo.

Uso:
    python scripts/cargar_catalogo.py --archivo ../Extractor_bd/captura2.0_tiendason/productos_extraidos.csv --reemplazar

--reemplazar borra ventas, cajas, devoluciones, abonos, egresos y productos de
prueba (CASCADE) y reinicia los consecutivos. No toca usuarios, clientes,
medios de pago, sucursales ni configuración.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, insert, select, text

from app.database import async_session_factory, engine
from app.models.producto import CodigoBarras, Producto
from app.models.sucursal import Sucursal

LOTE = 500
NOMBRE_MAX = 200


def _decimal(valor: str | None) -> Decimal:
    limpio = (valor or "").strip().replace(".", "").replace(",", ".")
    if not limpio:
        return Decimal("0")
    try:
        return Decimal(limpio)
    except InvalidOperation:
        return Decimal("0")


def _entero(valor: str | None) -> int:
    return int(_decimal(valor))


def leer_filas(archivo: Path) -> list[dict]:
    texto = archivo.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(texto.splitlines(), delimiter=";"))


async def cargar(archivo: Path, reemplazar: bool, id_sucursal: int | None) -> int:
    filas = leer_filas(archivo)
    if not filas:
        print("El archivo no tiene filas.")
        return 1

    async with async_session_factory() as db:
        existentes = (await db.execute(select(func.count()).select_from(Producto))).scalar() or 0
        if existentes and not reemplazar:
            print(f"ABORTADO: ya hay {existentes} productos. Use --reemplazar para reemplazarlos.")
            return 1

        if reemplazar:
            await db.execute(
                text(
                    "TRUNCATE TABLE productos, ventas, sesiones_caja, devoluciones, "
                    "abonos_cliente, egresos, consecutivos RESTART IDENTITY CASCADE"
                )
            )
            print(f"Reemplazados {existentes} productos y borrados los datos de prueba.")

        if id_sucursal is None:
            sucursal = (await db.execute(select(Sucursal).order_by(Sucursal.id_sucursal))).scalars().first()
        else:
            sucursal = await db.get(Sucursal, id_sucursal)
        if sucursal is None:
            print("No hay sucursal para asignar los productos.")
            return 1

        vistos: set[str] = set()
        insertados = 0
        codigos = 0
        codigos_duplicados = 0
        omitidos = 0
        lote: list[tuple[Producto, str | None]] = []

        async def volcar() -> None:
            nonlocal insertados, codigos, codigos_duplicados
            if not lote:
                return
            db.add_all([producto for producto, _ in lote])
            await db.flush()

            barcodes = []
            for producto, codigo in lote:
                insertados += 1
                if not codigo:
                    continue
                if codigo in vistos:
                    codigos_duplicados += 1
                    continue
                vistos.add(codigo)
                barcodes.append({"id_producto": producto.id_producto, "codigo_barras": codigo})

            if barcodes:
                await db.execute(insert(CodigoBarras), barcodes)
                codigos += len(barcodes)
            await db.flush()
            db.expunge_all()
            lote.clear()

        for fila in filas:
            nombre = (fila.get("nombre") or "").strip()
            if not nombre:
                omitidos += 1
                continue

            precio = _decimal(fila.get("precio_venta"))
            costo = _decimal(fila.get("costo"))
            producto = Producto(
                nombre_producto=nombre[:NOMBRE_MAX],
                precio_venta=float(precio),
                costo_compra=float(costo),
                stock_actual=float(_entero(fila.get("stock"))),
                stock_minimo_alerta=1,
                iva_porcentaje=0,
                id_sucursal=sucursal.id_sucursal,
            )
            codigo = (fila.get("codigo_barras") or "").strip() or None
            lote.append((producto, codigo))
            if len(lote) >= LOTE:
                await volcar()

        await volcar()
        await db.commit()

        total = (await db.execute(select(func.count()).select_from(Producto))).scalar() or 0
        total_codigos = (await db.execute(select(func.count()).select_from(CodigoBarras))).scalar() or 0

    print("Carga del catálogo terminada:")
    print(f"  Archivo: {archivo}")
    print(f"  Filas leídas: {len(filas)}")
    print(f"  Productos insertados: {insertados} (omitidos sin nombre: {omitidos})")
    print(f"  Códigos de barras: {codigos} (duplicados ignorados: {codigos_duplicados})")
    print(f"  Sucursal: {sucursal.nombre} (ID {sucursal.id_sucursal})")
    print(f"  En base: {total} productos, {total_codigos} códigos")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga el catálogo de productos desde el CSV del extractor.")
    parser.add_argument("--archivo", required=True, type=Path)
    parser.add_argument("--reemplazar", action="store_true", help="Borrar datos de prueba antes de cargar")
    parser.add_argument("--sucursal", type=int, default=None)
    args = parser.parse_args()

    if not args.archivo.exists():
        print(f"No existe el archivo: {args.archivo}")
        return 1
    return asyncio.run(cargar(args.archivo, args.reemplazar, args.sucursal))


if __name__ == "__main__":
    raise SystemExit(main())
