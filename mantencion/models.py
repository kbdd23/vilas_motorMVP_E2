from django.db import models
from django.utils import timezone


class PlanMantencion(models.Model):
    """Un plan pertenece a un tipo de equipo; un tipo puede tener varios planes."""

    id = models.AutoField(primary_key=True, db_column='id_plan')
    tipo_equipo = models.ForeignKey('flota.TipoEquipo', on_delete=models.PROTECT, db_column='id_tipo_equipo', related_name='planes')
    nombre = models.CharField(max_length=80)

    class Meta:
        db_table = 'plan_mantencion'

    def __str__(self):
        return self.nombre

    def serviciosOrdenados(self):
        """Servicios del plan ordenados por intervalo de horas ascendente."""
        return list(self.servicios.order_by('intervalo_horas'))


class ServicioPlan(models.Model):
    """Servicio de un plan (ej. mantención de 250h vs 1000h)."""

    id = models.AutoField(primary_key=True, db_column='id_servicio_plan')
    plan = models.ForeignKey('PlanMantencion', on_delete=models.PROTECT, db_column='id_plan', related_name='servicios')
    nombre = models.CharField(max_length=60)
    intervalo_horas = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'servicio_plan'

    def __str__(self):
        return self.nombre

    def insumosRequeridos(self):
        """Insumos (con su cantidad) que requiere este servicio."""
        return list(self.insumos.all())


class ServicioPlanInsumo(models.Model):
    """Receta: qué insumos y cuánto requiere un servicio (puente con dato extra)."""

    servicio_plan = models.ForeignKey('ServicioPlan', on_delete=models.CASCADE, db_column='id_servicio_plan', related_name='insumos')
    insumo = models.ForeignKey('insumos.Insumo', on_delete=models.CASCADE, db_column='id_insumo', related_name='servicios_plan')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'servicio_plan_insumo'
        # Django no soporta PK compuesta: la clave (servicio_plan, insumo) se fuerza con UNIQUE.
        constraints = [models.UniqueConstraint(fields=['servicio_plan', 'insumo'], name='pk_servicio_plan_insumo')]

    def __str__(self):
        return f'{self.servicio_plan} - {self.insumo}'


class OrdenTrabajo(models.Model):
    """Registro de la mantención ejecutada (la OT)."""

    class Tipo(models.TextChoices):
        PREVENTIVA = 'PREVENTIVA', 'Preventiva'
        CORRECTIVA = 'CORRECTIVA', 'Correctiva'

    class Estado(models.TextChoices):
        PROGRAMADA = 'PROGRAMADA', 'Programada'
        EN_CURSO = 'EN_CURSO', 'En curso'
        CERRADA = 'CERRADA', 'Cerrada'

    id = models.AutoField(primary_key=True, db_column='id_ot')
    equipo = models.ForeignKey('flota.Equipo', on_delete=models.PROTECT, db_column='id_equipo', related_name='ordenes_trabajo')
    servicio_plan = models.ForeignKey('ServicioPlan', on_delete=models.PROTECT, db_column='id_servicio_plan', null=True, blank=True, related_name='ordenes_trabajo')
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PROGRAMADA)
    numero_ot = models.CharField(max_length=20, unique=True)
    fecha_programada = models.DateField(null=True, blank=True)
    fecha_ejecucion = models.DateField(null=True, blank=True)
    horometro_cierre = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'orden_trabajo'

    def __str__(self):
        return self.numero_ot or f'OT {self.id}'

    def programar(self, fecha):
        """Asigna la fecha programada de ejecución."""
        self.fecha_programada = fecha
        self.save(update_fields=['fecha_programada'])

    def iniciar(self):
        """Pasa la OT de programada a en curso: el trabajo ya arrancó."""
        self.estado = self.Estado.EN_CURSO
        self.save(update_fields=['estado'])

    def registrarInsumo(self, insumo, cantidad, notas=None):
        """Registra un insumo real usado en esta OT."""
        return self.insumos.create(insumo=insumo, cantidad_usada=cantidad, notas=notas)

    def cerrar(self, horometro):
        """Cierra la OT: estado CERRADA, horómetro de cierre y fecha de ejecución."""
        self.estado = self.Estado.CERRADA
        self.horometro_cierre = horometro
        if not self.fecha_ejecucion:
            self.fecha_ejecucion = timezone.localdate()
        self.save(update_fields=['estado', 'horometro_cierre', 'fecha_ejecucion'])


class OrdenTrabajoInsumo(models.Model):
    """Insumos reales usados en una OT (puente con dato extra)."""

    orden_trabajo = models.ForeignKey('OrdenTrabajo', on_delete=models.CASCADE, db_column='id_ot', related_name='insumos')
    insumo = models.ForeignKey('insumos.Insumo', on_delete=models.CASCADE, db_column='id_insumo', related_name='ordenes_trabajo')
    cantidad_usada = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'orden_trabajo_insumo'
        # Django no soporta PK compuesta: la clave (orden_trabajo, insumo) se fuerza con UNIQUE.
        constraints = [models.UniqueConstraint(fields=['orden_trabajo', 'insumo'], name='pk_orden_trabajo_insumo')]

    def __str__(self):
        return f'{self.orden_trabajo} - {self.insumo}'
