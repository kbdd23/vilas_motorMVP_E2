"""Reglas de acceso a acciones que no son para cualquier cuenta.

La exportación de planillas queda reservada a planificadores y administradores:
son datos de toda la flota y del historial de mantención, no de consulta diaria.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

ROLES_EXPORTADORES = frozenset({'planificador', 'administrador'})


def nombreDelRol(usuario):
    """Devuelve el nombre del rol en minúsculas, o vacío si no tiene."""
    rol = getattr(usuario, 'rol', None)
    return (rol.nombre or '').strip().lower() if rol else ''


def puedeExportar(usuario):
    """True para cuentas activas con rol planificador o administrador."""
    if not usuario.is_authenticated:
        return False
    return nombreDelRol(usuario) in ROLES_EXPORTADORES


def requiere_rol_exportador(vista):
    """Corta la petición con 403 cuando el rol no permite exportar."""
    @wraps(vista)
    def envoltorio(request, *args, **kwargs):
        if not puedeExportar(request.user):
            raise PermissionDenied('Tu rol no permite exportar planillas.')
        return vista(request, *args, **kwargs)

    return envoltorio
