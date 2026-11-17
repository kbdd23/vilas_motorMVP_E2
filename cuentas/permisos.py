"""Reglas de acceso a acciones que no son para cualquier cuenta.

La exportación de planillas queda reservada al rol planificador: son datos de
toda la flota y del historial de mantención, no de consulta diaria.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

ROL_EXPORTADOR = 'planificador'


def nombreDelRol(usuario):
    """Devuelve el nombre del rol en minúsculas, o vacío si no tiene."""
    rol = getattr(usuario, 'rol', None)
    return (rol.nombre or '').strip().lower() if rol else ''


def puedeExportar(usuario):
    """True solo para cuentas activas con el rol planificador."""
    if not usuario.is_authenticated:
        return False
    return nombreDelRol(usuario) == ROL_EXPORTADOR


def requiere_rol_exportador(vista):
    """Corta la petición con 403 cuando el rol no permite exportar."""
    @wraps(vista)
    def envoltorio(request, *args, **kwargs):
        if not puedeExportar(request.user):
            raise PermissionDenied('Tu rol no permite exportar planillas.')
        return vista(request, *args, **kwargs)

    return envoltorio
