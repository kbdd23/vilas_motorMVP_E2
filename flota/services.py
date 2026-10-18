"""Qué se puede hacer con un equipo, según su estado.

El estado de un equipo mezcla dos cosas: dónde está la máquina y quién la tiene.
Sin un solo lugar que lo decida, cada regla del sistema terminaba interpretando el
estado por su cuenta, y los estados del medio (INTERNO) quedaban sin definir. Acá
vive esa decisión una sola vez: las vistas y los formularios preguntan, no deciden.
"""

from .models import Equipo

ESTADO = Equipo.Estado

# La tabla. Cada columna es una pregunta que el resto del sistema hace.
CAPACIDADES = {
    ESTADO.DISPONIBLE: {
        'se_arrienda': True,
        'entra_a_mantencion': True,
        'fuente_horometro': 'TECNICO',
        'cuenta_como_sin_devolver': False,
    },
    ESTADO.EN_FAENA: {
        'se_arrienda': False,
        'entra_a_mantencion': False,
        'fuente_horometro': 'CLIENTE',
        'cuenta_como_sin_devolver': True,
    },
    ESTADO.EN_MANTENIMIENTO: {
        'se_arrienda': False,
        'entra_a_mantencion': False,
        'fuente_horometro': 'TELEMETRIA',
        'cuenta_como_sin_devolver': False,
    },
    ESTADO.INTERNO: {
        'se_arrienda': False,
        'entra_a_mantencion': True,
        'fuente_horometro': 'INTERNO',
        'cuenta_como_sin_devolver': False,
    },
}


def _estadosCon(capacidad):
    """Estados de la tabla que responden sí a una capacidad."""
    return [estado for estado, capacidades in CAPACIDADES.items() if capacidades[capacidad]]


# Listas derivadas de la tabla, para las consultas que filtran por estado.
ESTADOS_ARRENDABLES = _estadosCon('se_arrienda')
ESTADOS_SIN_DEVOLVER = _estadosCon('cuenta_como_sin_devolver')


def capacidadesDe(equipo):
    """Las capacidades que da el estado actual del equipo."""
    return CAPACIDADES[ESTADO(equipo.estado)]


def puedeArrendarse(equipo):
    """True si el equipo puede salir a un cliente."""
    return capacidadesDe(equipo)['se_arrienda']


def puedeEntrarAMantencion(equipo):
    """True si se le puede iniciar una OT.

    Un equipo en faena está con el cliente; uno ya en mantenimiento tiene su OT en
    curso. Los dos quedan fuera, cada uno por su razón.
    """
    return capacidadesDe(equipo)['entra_a_mantencion']


def fuenteDeHorometro(equipo):
    """A quién se le pide el horómetro de este equipo."""
    return capacidadesDe(equipo)['fuente_horometro']


def cuentaComoSinDevolver(equipo):
    """True si cerró su arriendo y todavía no volvió a bodega."""
    return capacidadesDe(equipo)['cuenta_como_sin_devolver']


def mensajeDeBloqueo(equipo):
    """Por qué no se le puede iniciar una OT a este equipo.

    El texto cambia con el estado porque la salida es distinta: al que está en
    faena hay que esperarlo, y al que ya está en el taller hay que cerrarle la OT.
    """
    if equipo.estado == ESTADO.EN_FAENA:
        return 'No se puede iniciar: el equipo sigue en faena. Márcalo como disponible y verifica su disponibilidad.'
    if equipo.estado == ESTADO.EN_MANTENIMIENTO:
        return 'No se puede iniciar: el equipo ya está en mantenimiento, con una OT en curso.'
    return 'No se puede iniciar la OT con el estado actual del equipo.'
