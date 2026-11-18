"""Carga en la base todas las maquinarias de la empresa desde Equipos.xlsx.

Uso:  python manage.py cargar_flota
      python manage.py cargar_flota --archivo ruta/a/Equipos.xlsx
      python manage.py cargar_flota --simular      (muestra el resumen sin guardar)

Se puede ejecutar varias veces: un código que ya existe se actualiza (marca,
modelo, patente, tipo) sin tocar su estado ni su horómetro.
"""
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from flota.carga_flota import leer_planilla
from flota.models import Equipo, TipoEquipo

ARCHIVO_POR_DEFECTO = Path(settings.BASE_DIR) / 'flota' / 'datos' / 'Equipos.xlsx'


class Command(BaseCommand):
    help = 'Carga las maquinarias de la empresa desde flota/datos/Equipos.xlsx (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', default=str(ARCHIVO_POR_DEFECTO), help='Ruta de la planilla .xlsx')
        parser.add_argument('--simular', action='store_true', help='Lee y resume la planilla sin guardar nada.')

    def handle(self, *args, **options):
        ruta = Path(options['archivo'])
        if not ruta.exists():
            raise CommandError(f'No se encontró la planilla: {ruta}')
        try:
            equipos = leer_planilla(ruta)
        except ValueError as error:
            raise CommandError(str(error)) from error

        for tipo, cantidad in sorted(Counter(e['tipo_equipo'] for e in equipos).items()):
            self.stdout.write(f'  {tipo}: {cantidad}')
        if options['simular']:
            self.stdout.write(self.style.WARNING(f'Simulación: {len(equipos)} equipos leídos, nada guardado.'))
            return

        creados = actualizados = 0
        with transaction.atomic():
            tipos = {}
            for datos in equipos:
                nombre = datos['tipo_equipo']
                if nombre not in tipos:
                    tipos[nombre], _ = TipoEquipo.objects.get_or_create(
                        nombre=nombre, defaults={'unidad_medida': datos['unidad_medida']}
                    )
                campos = {
                    'tipo_equipo': tipos[nombre],
                    'marca': datos['marca'],
                    'modelo': datos['modelo'],
                    'patente': datos['patente'],
                }
                equipo, creado = Equipo.objects.get_or_create(codigo=datos['codigo'], defaults=campos)
                if creado:
                    creados += 1
                    continue
                cambios = [campo for campo, valor in campos.items() if getattr(equipo, campo) != valor]
                if cambios:
                    for campo in cambios:
                        setattr(equipo, campo, campos[campo])
                    equipo.save(update_fields=cambios)
                    actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Flota cargada: {creados} equipos nuevos, {actualizados} actualizados, '
            f'{len(equipos) - creados - actualizados} sin cambios.'
        ))
