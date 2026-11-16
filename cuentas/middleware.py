"""Bloquea el uso del sistema a las cuentas que aún no confirman su correo."""
from django.shortcuts import redirect


class VerificacionPendienteMiddleware:
    """Manda a la pantalla del código a quien tiene la cuenta sin verificar."""

    # Rutas que se pueden usar sin la cuenta confirmada.
    RUTAS_LIBRES = ('/verificar/', '/login/', '/logout/', '/static/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if (
            usuario.is_authenticated
            and not usuario.email_verificado
            and not request.path.startswith(self.RUTAS_LIBRES)
        ):
            return redirect('cuentas:verificar')
        return self.get_response(request)


class SegundoFactorMiddleware:
    """Pide el código de verificación a quien acaba de iniciar sesión.

    Solo interviene si el formulario de login marcó la sesión como pendiente, así
    que una sesión que ya confirmó el código —o que no nació del formulario— pasa
    sin cambios.
    """

    RUTAS_LIBRES = (
        '/login/',
        '/logout/',
        '/verificacion/',
        '/verificar/',
        '/static/',
        '/recuperar-acceso/',
        '/restablecer/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        sesion = request.session
        pendiente = sesion.get('segundo_factor_pendiente')
        confirmado = sesion.get('segundo_factor_confirmado')

        if (
            request.user.is_authenticated
            and pendiente
            and not confirmado
            and not request.path.startswith(self.RUTAS_LIBRES)
        ):
            return redirect('cuentas:verificacion_dos_pasos')
        return self.get_response(request)
