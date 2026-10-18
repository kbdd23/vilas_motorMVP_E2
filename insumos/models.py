from django.db import models


class Insumo(models.Model):
    """Catálogo de insumos usados en la mantención de un equipo.

    Sin campo de stock: el sistema no gestiona inventario. (Alcance MVP)
    """

    id = models.AutoField(primary_key=True, db_column='id_insumo')
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    unidad_medida = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'insumo'

    def __str__(self):
        return self.nombre
