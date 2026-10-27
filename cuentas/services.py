"""Generación, envío y validación del código de verificación de cuenta."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

# Alfabeto sin caracteres que se confunden al leerlos (0/O, 1/I/L).
ALFABETO_CODIGO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
LARGO_CODIGO = 6
VIGENCIA_CODIGO = timedelta(minutes=30)


def generarCodigo():
    """Código alfanumérico de seis caracteres."""
    return ''.join(secrets.choice(ALFABETO_CODIGO) for _ in range(LARGO_CODIGO))


def enviarCodigoVerificacion(usuario):
    """Genera un código nuevo, lo guarda en la cuenta y lo manda por correo.

    El código anterior deja de servir en cuanto se genera el nuevo.
    """
    codigo = generarCodigo()
    usuario.codigo_verificacion = codigo
    usuario.codigo_expira = timezone.now() + VIGENCIA_CODIGO
    usuario.save(update_fields=['codigo_verificacion', 'codigo_expira'])

    send_mail(
        subject='Tu código de verificación — Vilas Motor',
        message=f'Tu código para confirmar la cuenta es: {codigo}\n\nVence en 30 minutos. Si no creaste esta cuenta, ignora este correo.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )
    return codigo


def codigoEsValido(usuario, codigo):
    """True si el código coincide y sigue vigente."""
    if not usuario.codigo_verificacion or not usuario.codigo_expira:
        return False
    if timezone.now() > usuario.codigo_expira:
        return False
    return secrets.compare_digest(usuario.codigo_verificacion, codigo)


def confirmarCuenta(usuario):
    """Marca la cuenta como verificada y borra el código ya usado."""
    usuario.email_verificado = True
    usuario.codigo_verificacion = ''
    usuario.codigo_expira = None
    usuario.save(update_fields=['email_verificado', 'codigo_verificacion', 'codigo_expira'])
