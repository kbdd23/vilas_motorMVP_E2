from django.core.management.base import BaseCommand
from django.db import transaction

from flota.models import Equipo

# Faenas reales de la zona de Iquique. Los equipos EN_FAENA se reparten entre
# ellas de forma equitativa; el resto queda en el taller de base.
FAENAS = [
    ("Puerto de Iquique", -20.2052, -70.1508),
    ("Zofri, Iquique", -20.2199, -70.1382),
    ("Alto Hospicio", -20.2646, -70.0932),
    ("Faena Pozo Almonte", -20.2574, -69.7919),
    ("Faena minera Cerro Colorado", -20.0424, -69.2576),
]
TALLER = ("Taller", -20.2448, -70.1393)


class Command(BaseCommand):
    help = "Puebla latitud, longitud y ubicacion de los equipos para el mapa de flota."

    def handle(self, *args, **options):
        equipos = list(Equipo.objects.all())
        indice_faena = 0
        actualizados = 0

        with transaction.atomic():
            for equipo in equipos:
                if equipo.estado == Equipo.Estado.EN_FAENA:
                    nombre, latitud, longitud = FAENAS[indice_faena % len(FAENAS)]
                    indice_faena += 1
                else:
                    nombre, latitud, longitud = TALLER

                equipo.latitud = latitud
                equipo.longitud = longitud
                equipo.ubicacion = nombre
                equipo.save(update_fields=["latitud", "longitud", "ubicacion"])
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(f"{actualizados} equipos georreferenciados.")
        )
