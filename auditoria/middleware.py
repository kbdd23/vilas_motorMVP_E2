"""Guarda el usuario y la IP de la petición en curso para la auditoría automática."""
from contextvars import ContextVar

_contexto = ContextVar('auditoria_contexto', default=(None, None))


def contexto_actual():
    """Devuelve (usuario, ip) de la petición en curso, o (None, None) fuera de una petición."""
    return _contexto.get()


class UsuarioActualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        if usuario is not None and not usuario.is_authenticated:
            usuario = None
        ip = request.META.get('REMOTE_ADDR')
        token = _contexto.set((usuario, ip))
        try:
            return self.get_response(request)
        finally:
            _contexto.reset(token)
