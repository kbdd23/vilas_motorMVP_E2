from decimal import Decimal

from django.db import models


class TipoEquipo(models.Model):
    """Categoría de equipos (Grúa horquilla, Generador) y su unidad de medida."""

    class UnidadMedida(models.TextChoices):
        HORAS = 'HORAS', 'Horas'
        KM = 'KM', 'Kilómetros'

    id = models.SmallAutoField(primary_key=True, db_column='id_tipo_equipo')
    nombre = models.CharField(max_length=60, unique=True)
    unidad_medida = models.CharField(max_length=5, choices=UnidadMedida.choices)

    class Meta:
        db_table = 'tipo_equipo'

    def __str__(self):
        return self.nombre


class Equipo(models.Model):
    """Inventario de equipos: la ficha física de cada máquina."""

    class Estado(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        EN_FAENA = 'EN_FAENA', 'En faena'
        EN_MANTENIMIENTO = 'EN_MANTENIMIENTO', 'En mantenimiento'
        INTERNO = 'INTERNO', 'Interno'

    id = models.AutoField(primary_key=True, db_column='id_equipo')
    tipo_equipo = models.ForeignKey(
        TipoEquipo,
        on_delete=models.PROTECT,
        db_column='id_tipo_equipo',
        related_name='equipos',
    )
    codigo = models.CharField(max_length=30, unique=True)
    patente = models.CharField(max_length=10, unique=True, null=True, blank=True)
    marca = models.CharField(max_length=50, null=True, blank=True)
    modelo = models.CharField(max_length=50, null=True, blank=True)
    numero_serie = models.CharField(max_length=50, unique=True, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    # De dónde vino el equipo al entrar a mantenimiento. Al cerrar la OT vuelve
    # ahí: un equipo interno sigue siendo interno después de pasar por el taller.
    estado_previo = models.CharField(max_length=20, choices=Estado.choices, null=True, blank=True)
    horometro_actual = models.DecimalField(max_digits=10, decimal_places=1, default=Decimal('0.0'))
    telemetria_id = models.CharField(max_length=40, null=True, blank=True)

    class Meta:
        db_table = 'equipo'

    def __str__(self):
        return self.codigo

    def cambiarEstado(self, estado):
        """Transiciona el estado del equipo y persiste el cambio.

        Entrar a mantenimiento es el único cambio que guarda de dónde se venía, así
        que es también el único que después sabe a dónde volver.
        """
        nuevo = self.Estado(estado)
        if nuevo == self.Estado.EN_MANTENIMIENTO:
            # Ya en el taller no hay origen que recordar: se conserva el que había.
            if self.estado != self.Estado.EN_MANTENIMIENTO:
                self.estado_previo = self.estado
        else:
            self.estado_previo = None
        self.estado = nuevo
        self.save(update_fields=['estado', 'estado_previo'])

    def volverDeMantenimiento(self):
        """Devuelve el equipo al estado del que vino, o a disponible si no consta."""
        self.cambiarEstado(self.estado_previo or self.Estado.DISPONIBLE)

    def actualizarHorometro(self, valor):
        """Actualiza el horómetro actual del equipo."""
        self.horometro_actual = valor
        self.save(update_fields=['horometro_actual'])

    def ultimaLectura(self):
        """Devuelve la lectura de horómetro más reciente, o None si no hay."""
        return self.lecturas.order_by('-fecha_hora').first()
