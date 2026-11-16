"""Ubicaciones de referencia para el mapa de flota.

Las coordenadas de ejemplo existen para que el panel se pueda revisar antes de
conectar telemetría real. El cálculo es determinista: el mismo código de equipo
siempre cae en la misma coordenada, así el mapa no baila entre siembras.
"""

from decimal import Decimal

# Faenas de ejemplo en la Región de Tarapacá: el mapa abre mirando esta zona.
FAENAS_DEMO = (
    ('Iquique', Decimal('-20.220800'), Decimal('-70.141400')),
    ('Alto Hospicio', Decimal('-20.271700'), Decimal('-70.104000')),
    ('Pozo Almonte', Decimal('-20.257200'), Decimal('-69.786400')),
    ('Pica', Decimal('-20.490600'), Decimal('-69.330300')),
)

# Medio grado de ancho basta para que los marcadores no se apilen en un punto.
DISPERSION = Decimal('0.05')


def ubicacionDemo(codigo):
    """Devuelve (latitud, longitud) estable para el código de un equipo."""
    semilla = sum(ord(caracter) for caracter in codigo)
    _, latitud_base, longitud_base = FAENAS_DEMO[semilla % len(FAENAS_DEMO)]

    # Dos restos distintos para que el desplazamiento no sea una diagonal perfecta.
    desplazamiento_lat = DISPERSION * Decimal((semilla % 19) - 9) / Decimal(9)
    desplazamiento_lng = DISPERSION * Decimal((semilla % 13) - 6) / Decimal(6)

    return (latitud_base + desplazamiento_lat, longitud_base + desplazamiento_lng)
