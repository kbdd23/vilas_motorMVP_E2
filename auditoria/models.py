from django.db import models


class Auditoria(models.Model):
    """Auditoría DML: registro automático de INSERT/UPDATE/DELETE."""

    class Operacion(models.TextChoices):
        INSERT = 'INSERT', 'Insert'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'

    id = models.BigAutoField(primary_key=True, db_column='id_auditoria')
    usuario = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, db_column='id_usuario', related_name='auditorias')
    fecha_hora = models.DateTimeField()
    entidad = models.CharField(max_length=40)
    id_registro = models.BigIntegerField()  # referencia genérica: apunta a la tabla 'entidad', no es FK
    operacion = models.CharField(max_length=10, choices=Operacion.choices)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    ip = models.CharField(max_length=45, null=True, blank=True)

    class Meta:
        db_table = 'auditoria'

    def __str__(self):
        return f'{self.entidad}.{self.id_registro} ({self.operacion})'


class ArchivoAdjunto(models.Model):
    """Archivo adjunto a una entidad (sin soft-delete: el backend borra al borrar)."""

    id = models.AutoField(primary_key=True, db_column='id_archivo')
    usuario_subio = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, db_column='id_usuario_subio', related_name='archivos_subidos')
    entidad = models.CharField(max_length=40)
    id_registro = models.BigIntegerField()  # referencia genérica: apunta a la tabla 'entidad'
    nombre_original = models.CharField(max_length=255)
    ruta = models.FileField(upload_to='adjuntos/', max_length=500)
    mime = models.CharField(max_length=100, null=True, blank=True)
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'archivo_adjunto'

    def __str__(self):
        return self.nombre_original
