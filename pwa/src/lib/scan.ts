/** Validación del campo de escaneo: rechaza QR y basura sin romper la venta en curso. */

export interface ResultadoEscaneo {
  ok: boolean;
  codigo?: string;
  motivo?: string;
}

function digitoVerificadorValido(codigo: string): boolean {
  const digitos = codigo.split("").map(Number);
  const verificador = digitos.pop();
  if (verificador === undefined) return false;
  let suma = 0;
  digitos.reverse().forEach((digito, indice) => {
    suma += digito * (indice % 2 === 0 ? 3 : 1);
  });
  return (10 - (suma % 10)) % 10 === verificador;
}

export function normalizarEscaneo(entrada: string): ResultadoEscaneo {
  const codigo = (entrada ?? "").trim();

  if (!codigo) return { ok: false };

  // Un lector en modo teclado puede enviar la URL de un QR: se descarta sin tocar la venta.
  if (/https?:\/\//i.test(codigo) || codigo.includes("://") || /\s/.test(codigo)) {
    return { ok: false, motivo: "Lectura no válida (parece un código QR). Escanee el código de barras." };
  }

  if (codigo.length > 24) {
    return { ok: false, motivo: "El código es demasiado largo para ser un código de barras." };
  }

  if (!/^[A-Za-z0-9._-]+$/.test(codigo)) {
    return { ok: false, motivo: "El código contiene caracteres no válidos." };
  }

  if (/^\d+$/.test(codigo) && [8, 12, 13, 14].includes(codigo.length)) {
    if (!digitoVerificadorValido(codigo)) {
      return { ok: false, motivo: "El código no pasa la validación del dígito verificador." };
    }
  }

  return { ok: true, codigo };
}
