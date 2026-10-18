from django.db import models


class ArriendoQuerySet(models.QuerySet):
    """Consultas de arriendos, con la regla de vigencia en un solo lugar."""

    def vigentes(self):
        """Arriendos abiertos: los que todavía no tienen fecha de término."""
        return self.filter(fecha_termino__isnull=True)


class Arriendo(models.Model):
    """Contrato de arriendo de un equipo a un cliente.

    La vigencia se infiere, no se almacena: un arriendo está vigente mientras no
    tenga fecha de término. Cerrar el contrato es fijar esa fecha, que es el día
    en que la máquina se devuelve.
    """

    id = models.AutoField(primary_key=True, db_column='id_arriendo')
    equipo = models.ForeignKey('flota.Equipo', on_delete=models.PROTECT, db_column='id_equipo', related_name='arriendos')
    cliente = models.ForeignKey('cuentas.Cliente', on_delete=models.PROTECT, db_column='id_cliente', related_name='arriendos')
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)

    objects = ArriendoQuerySet.as_manager()

    class Meta:
        db_table = 'arriendo'

    def __str__(self):
        return f'{self.equipo} - {self.cliente}'

    def cerrar(self, fecha_termino):
        """Cierra el arriendo fijando la fecha de término."""
        self.fecha_termino = fecha_termino
        self.save(update_fields=['fecha_termino'])

    def estaVigente(self):
        """True mientras el arriendo no tenga fecha de término."""
        return self.fecha_termino is None
