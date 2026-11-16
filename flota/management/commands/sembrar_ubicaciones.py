"""Ubica los equipos que todavía no reportan posición.

Sirve para revisar el mapa de flota antes de conectar telemetría real: es
idempotente y solo toca equipos con latitud nula, así que nunca pisa una
coordenada que venga de un GPS.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from flota.models import Equipo
from flota.ubicaciones import ubicacionDemo


class Command(BaseCommand):
    help = 'Asigna coordenadas de ejemplo a los equipos sin posición (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Cantidad máxima de equipos a ubicar en esta pasada.',
        )

    def handle(self, *args, **options):
        pendientes = Equipo.objects.filter(latitud__isnull=True).order_by('codigo')
        if options['limite']:
            pendientes = pendientes[:options['limite']]

        ahora = timezone.now()
        equipos = []
        for equipo in pendientes:
            equipo.latitud, equipo.longitud = ubicacionDemo(equipo.codigo)
            equipo.ultima_senal = ahora
            equipos.append(equipo)

        Equipo.objects.bulk_update(equipos, ['latitud', 'longitud', 'ultima_senal'])
        self.stdout.write(
            self.style.SUCCESS(f'Equipos ubicados: {len(equipos)}')
        )
