from django.db import models
from django.utils import timezone


class LecturaHorometro(models.Model):
    """Historial de horas reales reportadas por el cliente o el técnico."""

    class Fuente(models.TextChoices):
        """Esto sirve para identificar de donde vino el dato del horometro"""

        CLIENTE = 'CLIENTE', 'Cliente'
        TECNICO = 'TECNICO', 'Técnico'
        PLANIFICACION = 'PLANIFICACION', 'Planificación'
        TELEMETRIA = 'TELEMETRIA', 'Telemetría'
        INTERNO = 'INTERNO', 'Interno'

    id = models.BigAutoField(primary_key=True, db_column='id_lectura')
    equipo = models.ForeignKey('flota.Equipo', on_delete=models.PROTECT, db_column='id_equipo', related_name='lecturas')
    usuario = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, db_column='id_usuario', related_name='lecturas')
    valor = models.DecimalField(max_digits=10, decimal_places=1)
    fecha_hora = models.DateTimeField()
    fuente = models.CharField(max_length=15, choices=Fuente.choices)
    validada = models.BooleanField(default=False)
    observacion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'lectura_horometro'

    def __str__(self):
        return f'{self.equipo} @ {self.valor} ({self.fecha_hora})'


# A quién se le puede pedir el horómetro de un equipo. La planificación no está:
# el dato se le pide a alguien (el cliente que tiene la máquina, el técnico que la
# revisa, quien la usa de forma interna o la telemetría del equipo), no a un área
# interna. Los valores coinciden con LecturaHorometro.Fuente porque la lectura que
# cierra la solicitud hereda esta fuente.
FUENTES_DE_SOLICITUD = [
    ('CLIENTE', 'Cliente'),
    ('TECNICO', 'Técnico'),
    ('TELEMETRIA', 'Telemetría'),
    ('INTERNO', 'Interno'),
]


class SolicitudHorometro(models.Model):
    """Petición del horómetro de un equipo, dirigida a una fuente.

    Se resuelve en un solo paso: el planificador ingresa el dato que recibió, y
    eso la cierra y la vincula a la lectura. Mientras no lo haga la solicitud
    sigue pendiente sin importar cuánto tiempo pase, y eso es lo que la mantiene
    en la bandeja de trabajo. Si se equivocó, la borra.

    'fuente' dice a quién se le pidió el dato, y no es un detalle decorativo:
    gobierna qué equipos se pueden elegir (al técnico se le pide con la máquina
    en bodega, al cliente con la máquina en faena, la telemetría no depende del
    estado) y la lectura que la cierra hereda esa fuente.

    'cliente' queda nulo cuando no hay cliente involucrado: una solicitud al
    técnico o a la telemetría no se le pide a nadie de afuera.

    'fecha_resolucion' guarda cuándo dejó de estar pendiente y es la que gobierna
    la ventana de trazabilidad, igual que 'fecha_termino' en los arriendos.
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        CUMPLIDA = 'CUMPLIDA', 'Cumplida'

    id = models.AutoField(primary_key=True, db_column='id_solicitud')
    equipo = models.ForeignKey('flota.Equipo', on_delete=models.PROTECT, db_column='id_equipo', related_name='solicitudes_horometro')
    cliente = models.ForeignKey('cuentas.Cliente', on_delete=models.PROTECT, db_column='id_cliente', related_name='solicitudes_horometro', null=True, blank=True)
    usuario_solicita = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, db_column='id_usuario_solicita', related_name='solicitudes_realizadas')
    fuente = models.CharField(max_length=15, choices=FUENTES_DE_SOLICITUD)
    fecha_solicitud = models.DateTimeField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE) #Una solicitud siempre nace como pendiente
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    lectura = models.OneToOneField(LecturaHorometro, on_delete=models.PROTECT, db_column='id_lectura', null=True, blank=True, related_name='solicitud')

    class Meta:
        db_table = 'solicitud_horometro'

    def __str__(self):
        return f'{self.equipo} ({self.get_fuente_display()}, {self.estado})'

    def estaPendiente(self):
        """True mientras falte ingresar el dato que se pidió."""
        return self.estado == self.Estado.PENDIENTE

    def esDelCliente(self):
        """True si el dato se le pidió al cliente que tiene la máquina."""
        return self.fuente == 'CLIENTE'

    def cumplir(self, lectura):
        """Marca la solicitud cumplida y la vincula a la lectura reportada."""
        self.estado = self.Estado.CUMPLIDA
        self.lectura = lectura
        self.fecha_resolucion = timezone.now()
        self.save(update_fields=['estado', 'lectura', 'fecha_resolucion'])
