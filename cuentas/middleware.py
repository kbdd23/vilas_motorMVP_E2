"""Bloquea el uso del sistema a las cuentas que aún no confirman su correo."""
from django.shortcuts import redirect


class VerificacionPendienteMiddleware:
    """Manda a la pantalla del código a quien tiene la cuenta sin verificar."""

    # Rutas que se pueden usar sin la cuenta confirmada.
    RUTAS_LIBRES = ('/verificar/', '/login/', '/registro/', '/logout/', '/static/')

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
