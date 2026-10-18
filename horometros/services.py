from decimal import Decimal, InvalidOperation

from arriendos.models import Arriendo
from flota.services import fuenteDeHorometro


class ValidadorDatos:
    """Valida datos de entrada del dominio, en particular lecturas de horómetro."""

    def validar(self, equipo, valor) -> bool:
        """True si 'valor' es una lectura de horómetro válida para el equipo.

        Reglas:
        - No puede ser negativa.
        - No puede ser menor al horómetro actual (el horómetro no retrocede).
        """
        try:
            lectura = Decimal(valor)
        except (InvalidOperation, TypeError, ValueError):
            return False
        if lectura < 0:
            return False
        return lectura >= equipo.horometro_actual


def arrendatarioDelEquipo(equipo):
    """Cliente que tiene la máquina, o None si nunca se arrendó.

    Da igual si el contrato sigue vigente o ya se cerró: mientras la máquina esté
    en faena, quien la tiene es el último arrendatario, y a él se le pide el dato.
    """
    ultimo = (
        Arriendo.objects.filter(equipo=equipo)
        .select_related('cliente')
        .order_by('-fecha_inicio', '-id')
        .first()
    )
    return ultimo.cliente if ultimo else None


def fuenteSugerida(equipo):
    """Fuente más probable para pedir el horómetro de un equipo.

    Es solo una sugerencia para el enlace de la ficha, y sale de la tabla de
    capacidades del estado: así la ficha y el formulario de solicitud no pueden
    discrepar sobre a quién le corresponde el dato.
    """
    return fuenteDeHorometro(equipo)
