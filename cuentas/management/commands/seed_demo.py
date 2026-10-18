"""Carga los datos de demostración de Vilas Motor.

Es solo el punto de entrada: la data y la lógica viven en vilas_motor/dataseed.py.
"""
from django.core.management.base import BaseCommand

from vilas_motor.dataseed import sembrar


class Command(BaseCommand):
    help = 'Carga el dataset de demostración de Vilas Motor (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Elimina los registros de demostración antes de volver a cargarlos.',
        )

    def handle(self, *args, **options):
        resumen = sembrar(flush=options['flush'])
        for tabla, cantidad in resumen.items():
            self.stdout.write(f'  {tabla}: {cantidad}')
        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))
