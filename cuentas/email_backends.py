"""Envío de correo por la API HTTP de Brevo.

Vercel bloquea los puertos SMTP salientes (25, 465 y 587), así que el correo
sale por HTTPS, que ningún host bloquea.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

URL_ENVIO = 'https://api.brevo.com/v3/smtp/email'


class BrevoEmailBackend(BaseEmailBackend):
    """Manda los mensajes con la API transaccional de Brevo."""

    def send_messages(self, email_messages):
        enviados = 0
        for mensaje in email_messages:
            try:
                self._enviar(mensaje)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                enviados += 1
        return enviados

    def _enviar(self, mensaje):
        cuerpo = {
            'sender': {'email': settings.BREVO_REMITENTE, 'name': 'Vilas Motor'},
            'to': [{'email': destinatario} for destinatario in mensaje.to],
            'subject': mensaje.subject,
            'textContent': mensaje.body,
        }
        peticion = urllib.request.Request(
            URL_ENVIO,
            data=json.dumps(cuerpo).encode('utf-8'),
            headers={
                'api-key': settings.BREVO_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(peticion, timeout=15) as respuesta:
                respuesta.read()
        except urllib.error.HTTPError as error:
            detalle = error.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Brevo rechazó el envío: {error.code} {detalle}') from error
