"""Auditoría DML automática: registra INSERT, UPDATE y DELETE de las entidades de negocio.

Solo se registra cuando hay un usuario autenticado en la petición; las cargas de datos
(seed_demo, migraciones, consola) no generan filas de auditoría.
"""
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_delete, post_save, pre_save
from django.forms.models import model_to_dict
from django.utils import timezone

from .middleware import contexto_actual
from .models import Auditoria

# Entidades auditadas (app_label.modelo). Se excluyen la propia auditoría, los adjuntos y los datos de sesión.
AUDITADAS = {
    'arriendos.arriendo', 'cuentas.cliente', 'cuentas.usuario', 'flota.tipoequipo', 'flota.equipo',
    'horometros.lecturahorometro', 'horometros.solicitudhorometro', 'insumos.insumo',
    'mantencion.planmantencion', 'mantencion.servicioplan', 'mantencion.servicioplaninsumo',
    'mantencion.ordentrabajo', 'mantencion.ordentrabajoinsumo',
}
CAMPOS_SENSIBLES = {'password', 'last_login'}


def _auditada(instancia):
    return instancia._meta.label_lower in AUDITADAS


def _foto(instancia):
    datos = model_to_dict(instancia)
    for campo in CAMPOS_SENSIBLES:
        datos.pop(campo, None)
    return json.loads(json.dumps(datos, cls=DjangoJSONEncoder, default=str))


def _registrar(instancia, operacion, anterior, nuevo):
    usuario, ip = contexto_actual()
    if usuario is None:
        return
    Auditoria.objects.create(
        usuario=usuario, fecha_hora=timezone.now(), entidad=instancia._meta.db_table,
        id_registro=instancia.pk, operacion=operacion,
        valor_anterior=anterior, valor_nuevo=nuevo, ip=ip,
    )


def antes_de_guardar(sender, instance, raw=False, **kwargs):
    if raw or not _auditada(instance):
        return
    instance._auditoria_anterior = None
    if instance.pk:
        previo = sender._default_manager.filter(pk=instance.pk).first()
        if previo is not None:
            instance._auditoria_anterior = _foto(previo)


def despues_de_guardar(sender, instance, created, raw=False, **kwargs):
    if raw or not _auditada(instance):
        return
    _registrar(instance, 'INSERT' if created else 'UPDATE',
               None if created else getattr(instance, '_auditoria_anterior', None), _foto(instance))


def despues_de_borrar(sender, instance, **kwargs):
    if not _auditada(instance):
        return
    _registrar(instance, 'DELETE', _foto(instance), None)


def conectar():
    pre_save.connect(antes_de_guardar, dispatch_uid='auditoria_pre_save')
    post_save.connect(despues_de_guardar, dispatch_uid='auditoria_post_save')
    post_delete.connect(despues_de_borrar, dispatch_uid='auditoria_post_delete')
