/** Impresión del doble comprobante desde el navegador (respaldo de la ticketera ESC/POS). */

export interface TiquetePayload {
  lineas_cliente: string[];
  lineas_copia: string[];
  copias: number;
}

function escaparHtml(texto: string): string {
  return texto
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function bloque(lineas: string[]): string {
  return `<pre>${escaparHtml(lineas.join("\n"))}</pre>`;
}

export function imprimirTiquete(payload: TiquetePayload): void {
  const copias = payload.copias >= 2 ? [payload.lineas_cliente, payload.lineas_copia] : [payload.lineas_cliente];
  const cuerpo = copias.map((lineas) => bloque(lineas)).join('<div class="corte"></div>');

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Tiquete</title>
<style>
  @page { size: 80mm auto; margin: 0; }
  body { margin: 0; padding: 4mm; font-family: "Courier New", monospace; color: #000; background: #fff; }
  pre { font-size: 11px; line-height: 1.25; margin: 0; white-space: pre-wrap; word-break: break-word; }
  .corte { page-break-after: always; height: 6mm; }
</style></head><body>${cuerpo}</body></html>`;

  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  document.body.appendChild(iframe);

  const doc = iframe.contentWindow?.document;
  if (!doc) {
    iframe.remove();
    return;
  }
  doc.open();
  doc.write(html);
  doc.close();

  iframe.onload = () => {
    iframe.contentWindow?.focus();
    iframe.contentWindow?.print();
    window.setTimeout(() => iframe.remove(), 1500);
  };
}

/** Tiquete de respaldo cuando la venta se registró sin conexión. */
export function imprimirTiqueteLocal(datos: {
  negocio: string;
  uuid: string;
  fecha: string;
  items: { nombre: string; cantidad: number; precio: number; subtotal: number }[];
  total: number;
  pagos: { metodo: string; monto: number }[];
  pendienteSincronizar: boolean;
}): void {
  const ancho = 40;
  const lineas: string[] = [
    datos.negocio.slice(0, ancho).padStart(Math.ceil((ancho + datos.negocio.length) / 2)).slice(0, ancho),
    "-".repeat(ancho),
    `Fecha: ${datos.fecha}`,
    `UUID ${datos.uuid}`,
    "-".repeat(ancho),
  ];

  for (const item of datos.items) {
    lineas.push(item.nombre.slice(0, ancho));
    lineas.push(`  ${item.cantidad} x ${Math.round(item.precio).toLocaleString("es-CO")}`.padEnd(24) + Math.round(item.subtotal).toLocaleString("es-CO").padStart(16));
  }

  lineas.push("-".repeat(ancho));
  lineas.push("TOTAL".padEnd(24) + Math.round(datos.total).toLocaleString("es-CO").padStart(16));
  lineas.push("-".repeat(ancho));
  for (const pago of datos.pagos) {
    lineas.push(`${pago.metodo}`.padEnd(24) + Math.round(pago.monto).toLocaleString("es-CO").padStart(16));
  }
  lineas.push("-".repeat(ancho));
  if (datos.pendienteSincronizar) lineas.push("*** PENDIENTE DE SINCRONIZAR ***");
  lineas.push("Gracias por su compra");

  imprimirTiquete({ lineas_cliente: lineas, lineas_copia: lineas, copias: 2 });
}
