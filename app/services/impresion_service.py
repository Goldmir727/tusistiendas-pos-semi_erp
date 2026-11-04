from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.exceptions import PrinterError

settings = get_settings()

DENOMINACIONES_IMPRESORA = {
    "billete_50000": "$50.000",
    "billete_20000": "$20.000",
    "billete_10000": "$10.000",
    "billete_5000": "$5.000",
    "billete_2000": "$2.000",
    "billete_1000": "$1.000",
    "moneda_500": "$500",
    "moneda_200": "$200",
    "moneda_100": "$100",
    "moneda_50": "$50",
}


def get_printer():
    try:
        from escpos.printer import Usb, Network

        if settings.IMPRESORA_TIPO == "usb":
            vid = int(settings.IMPRESORA_USB_VID, 16)
            pid = int(settings.IMPRESORA_USB_PID, 16)
            return Usb(vid, pid)
        elif settings.IMPRESORA_TIPO == "red":
            return Network(settings.IMPRESORA_RED_HOST, settings.IMPRESORA_RED_PORT)
    except Exception as e:
        raise PrinterError(f"No se pudo conectar impresora: {e}")


def imprimir_ticket_venta(venta_data: dict[str, Any], detalles: list[dict], pagos: list[dict]) -> None:
    p = get_printer()
    try:
        p.set(align="center", bold=True, double_height=True)
        p.text("=== TICKET DE VENTA ===\n")
        p.set(align="left", bold=False, double_height=False)
        p.text(f"Venta #: {venta_data['id_venta']}\n")
        p.text(f"Fecha: {venta_data['fecha_venta']}\n")
        p.text(f"Cajero: {venta_data.get('cajero', 'N/A')}\n")
        p.text("-" * 40 + "\n")

        for det in detalles:
            p.text(f"{det['nombre'][:25]:25} {det['cantidad']:>5} x ${det['precio']:>10.2f}\n")

        p.text("-" * 40 + "\n")
        p.text(f"{'Subtotal:':<30} ${venta_data['subtotal']:>10.2f}\n")
        p.text(f"{'IVA:':<30} ${venta_data['impuestos']:>10.2f}\n")
        p.text(f"{'TOTAL:':<30} ${venta_data['total']:>10.2f}\n")
        p.text("-" * 40 + "\n")

        for pago in pagos:
            p.text(f"Pagado: ${pago['monto']:.2f} ({pago['metodo']})\n")

        p.text("\n")
        p.set(align="center")
        p.text("Gracias por su compra!\n")
        p.cut()
    except Exception as e:
        raise PrinterError(f"Error al imprimir ticket: {e}")
    finally:
        p.close()


def imprimir_comprobante_pago(pago_data: dict, copias: int = 2) -> None:
    for i in range(copias):
        p = get_printer()
        try:
            p.set(align="center", bold=True, double_height=True)
            p.text(f"=== COMPROBANTE DE PAGO ===\n")
            p.text(f"Copia {i + 1}/{copias}\n")
            p.set(align="left", bold=False, double_height=False)
            p.text("-" * 40 + "\n")
            p.text(f"Empleado: {pago_data.get('empleado', 'N/A')}\n")
            p.text(f"Fecha: {pago_data.get('fecha', 'N/A')}\n")
            p.text(f"Metodo: {pago_data.get('metodo', 'N/A')}\n")
            p.text(f"Total: ${pago_data.get('monto_total', 0):.2f}\n")
            p.text("-" * 40 + "\n")

            for turno in pago_data.get("turnos", []):
                p.text(f"Turno {turno['fecha']}: ${turno['monto']:.2f}\n")

            p.text("\n")
            p.set(align="center")
            p.text("_" * 30 + "\n")
            p.text("Firma empleado\n")
            p.text("\n")
            p.cut()
        except Exception as e:
            raise PrinterError(f"Error al imprimir comprobante: {e}")
        finally:
            p.close()


def abrir_cajon() -> None:
    p = get_printer()
    try:
        p.cashdraw(2)
    except Exception as e:
        raise PrinterError(f"Error al abrir cajón: {e}")
    finally:
        p.close()


ANCHO_TIQUETE = 40


def construir_lineas_tiquete(
    negocio: dict[str, Any],
    venta: dict[str, Any],
    items: list[dict[str, Any]],
    pagos: list[dict[str, Any]],
    copia: str = "CLIENTE",
) -> list[str]:
    """Arma el tiquete en texto plano de 40 columnas (ESC/POS y respaldo HTML)."""
    ancho = ANCHO_TIQUETE
    lineas: list[str] = [str(negocio.get("nombre") or "TuSisTiendas")[:ancho].center(ancho)]
    if negocio.get("nit"):
        lineas.append(f"NIT {negocio['nit']}"[:ancho].center(ancho))
    if negocio.get("direccion"):
        lineas.append(str(negocio["direccion"])[:ancho].center(ancho))
    if negocio.get("telefono"):
        lineas.append(f"Tel {negocio['telefono']}"[:ancho].center(ancho))

    lineas.append("-" * ancho)
    lineas.append(f"Tiquete No. {venta['consecutivo']}")
    lineas.append(f"Fecha: {venta['fecha']}")
    lineas.append(f"Cajero: {venta['cajero']}")
    lineas.append(f"Cliente: {venta['cliente']}")
    lineas.append("-" * ancho)

    for item in items:
        lineas.append(str(item["nombre"])[:ancho])
        izquierda = f"  {item['cantidad']:g} x {item['precio']:,.0f}"
        lineas.append(f"{izquierda:<24}{item['subtotal']:>16,.0f}")

    lineas.append("-" * ancho)
    lineas.append(f"{'Subtotal':<24}{venta['subtotal']:>16,.0f}")
    lineas.append(f"{'Impuestos':<24}{venta['impuestos']:>16,.0f}")
    lineas.append(f"{'TOTAL':<24}{venta['total']:>16,.0f}")
    lineas.append("-" * ancho)

    for pago in pagos:
        lineas.append(f"{str(pago['metodo'])[:20]:<24}{pago['monto']:>16,.0f}")
        if pago.get("vuelto"):
            lineas.append(f"{'  Cambio':<24}{pago['vuelto']:>16,.0f}")

    lineas.append("-" * ancho)
    lineas.append(f"UUID {venta['uuid']}"[:ancho])
    lineas.append(f"*** {copia} ***".center(ancho))
    lineas.append(str(negocio.get("mensaje") or "Gracias por su compra")[:ancho].center(ancho))
    return lineas


def _imprimir_lineas(lineas: list[str], abrir_caja: bool = False) -> None:
    p = get_printer()
    try:
        if abrir_caja:
            p.cashdraw(2)
        for linea in lineas:
            p.text(linea + "\n")
        p.text("\n")
        p.cut()
    except Exception as e:
        raise PrinterError(f"Error al imprimir tiquete: {e}")
    finally:
        p.close()


def imprimir_ticket_doble(lineas_cliente: list[str], lineas_copia: list[str]) -> None:
    """Doble comprobante: original para el cliente y copia para el negocio (RF-09)."""
    _imprimir_lineas(lineas_cliente, abrir_caja=True)
    _imprimir_lineas(lineas_copia)
