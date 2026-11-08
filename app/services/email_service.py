from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.config import get_settings
from app.exceptions import ValidationError

settings = get_settings()


def _enviar_sync(destino: str, asunto: str, cuerpo: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = destino
    msg["Subject"] = asunto
    msg.set_content(cuerpo)

    if settings.SMTP_SSL:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.ehlo()
            if settings.SMTP_STARTTLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)


async def enviar_codigo_verificacion(destino: str, codigo: str, minutos: int) -> None:
    if settings.AUTH_2FA_DEV_MODE or not settings.SMTP_HOST:
        import logging

        logging.getLogger("pos.email").warning(
            "2FA dev mode: codigo %s para %s (expira en %s min)", codigo, destino, minutos
        )
        return

    asunto = "Codigo de verificacion - POS System"
    cuerpo = (
        f"Tu codigo de verificacion es: {codigo}\n\n"
        f"Expira en {minutos} minutos.\n"
        "Si no solicitaste este codigo, ignora este mensaje."
    )
    try:
        await asyncio.to_thread(_enviar_sync, destino, asunto, cuerpo)
    except Exception as exc:
        raise ValidationError(f"No se pudo enviar el codigo de verificacion: {exc}") from exc