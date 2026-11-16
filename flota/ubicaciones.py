"""Ubicaciones de referencia para el mapa de flota.

Las coordenadas de ejemplo existen para que el panel se pueda revisar antes de
conectar telemetría real. El cálculo es determinista: el mismo código de equipo
siempre cae en la misma coordenada, así el mapa no baila entre siembras.

La dispersión es seudoleatoria y no modular: los restos de una división formaban
una rejilla visible sobre el mapa, que delataba datos falsos.
"""

import hashlib
from decimal import Decimal

# Faenas de ejemplo en la Región de Tarapacá, todas en tierra firme: si el centro
# cae en la costa, media flota termina dibujada en el océano.
FAENAS_DEMO = (
    ('Iquique', Decimal('-20.220000'), Decimal('-70.140000')),
    ('Alto Hospicio', Decimal('-20.270000'), Decimal('-70.105000')),
    ('Pozo Almonte', Decimal('-20.256000'), Decimal('-69.786000')),
    ('Pica', Decimal('-20.490000'), Decimal('-69.330000')),
)

DISPERSION = Decimal('0.008')


def _desplazamiento(semilla, eje):
    """Devuelve un decimal entre -1 y 1, estable para la misma semilla y eje."""
    digest = hashlib.sha256(f'{semilla}:{eje}'.encode('utf-8')).hexdigest()
    entero = int(digest[:8], 16)
    return Decimal(entero % 2001 - 1000) / Decimal(1000)


def ubicacionDemo(codigo):
    """Devuelve (latitud, longitud) estable para el código de un equipo."""
    digest = hashlib.sha256(codigo.encode('utf-8')).digest()
    _, latitud_base, longitud_base = FAENAS_DEMO[digest[0] % len(FAENAS_DEMO)]

    latitud = latitud_base + DISPERSION * _desplazamiento(codigo, 'lat')
    longitud = longitud_base + DISPERSION * _desplazamiento(codigo, 'lng')

    return (round(latitud, 6), round(longitud, 6))
