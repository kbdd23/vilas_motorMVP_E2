from decimal import Decimal

from django.utils import timezone

from horometros.models import LecturaHorometro

from .models import OrdenTrabajo, ServicioPlan


class CalculadoraProximoServicio:
    """Calcula cuándo corresponde la próxima mantención de un equipo.

    Regla de negocio: un equipo pertenece a un tipo de equipo, que tiene planes,
    y cada plan tiene servicios con un intervalo de horas. El próximo servicio es
    aquel cuyo vencimiento está más cerca, medido como la diferencia entre el
    horómetro actual del equipo y el horómetro de cierre de su última OT cerrada
    para ese servicio.
    """

    def __init__(self, umbral_alerta_horas):
        self.umbral_alerta_horas = umbral_alerta_horas

    def serviciosDelEquipo(self, equipo):
        """Servicios con intervalo definido para el tipo de equipo."""
        return ServicioPlan.objects.filter(
            plan__tipo_equipo=equipo.tipo_equipo,
            intervalo_horas__isnull=False,
        )

    def ultimoHorometroMantencion(self, equipo, servicio):
        """Horómetro de cierre de la última OT cerrada para un servicio, o 0."""
        ultima = (
            OrdenTrabajo.objects.filter(
                equipo=equipo,
                servicio_plan=servicio,
                estado=OrdenTrabajo.Estado.CERRADA,
                horometro_cierre__isnull=False,
            )
            .order_by('-horometro_cierre')
            .first()
        )
        return ultima.horometro_cierre if ultima else Decimal('0.0')

    def horasRestantes(self, equipo, servicio):
        """Horas que faltan para vencer el intervalo del servicio (negativo si venció)."""
        ultimo = self.ultimoHorometroMantencion(equipo, servicio)
        horas_transcurridas = equipo.horometro_actual - ultimo
        return Decimal(servicio.intervalo_horas) - horas_transcurridas

    def calcularProximoServicio(self, equipo):
        """Devuelve el próximo servicio a realizar, o None si el equipo no tiene servicios."""
        servicios = list(self.serviciosDelEquipo(equipo))
        if not servicios:
            return None
        return min(servicios, key=lambda servicio: self.horasRestantes(equipo, servicio))

    def estaEnAlerta(self, equipo, servicio=None):
        """True si el próximo servicio está dentro del umbral de alerta."""
        proximo = servicio or self.calcularProximoServicio(equipo)
        if proximo is None:
            return False
        return self.horasRestantes(equipo, proximo) <= self.umbral_alerta_horas

    def proximosServicios(self, equipos):
        """Versión en bloque de calcularProximoServicio/horasRestantes para varios equipos.

        Usa 2 consultas en total (servicios y último cierre por equipo y servicio) en vez de
        una por cada equipo y servicio. Devuelve {id_equipo: (servicio | None, horas_restantes | None)}.
        """
        from django.db.models import Max

        equipos = list(equipos)
        servicios_por_tipo = {}
        for servicio in ServicioPlan.objects.filter(
            plan__tipo_equipo__in={e.tipo_equipo_id for e in equipos}, intervalo_horas__isnull=False
        ).select_related('plan'):
            servicios_por_tipo.setdefault(servicio.plan.tipo_equipo_id, []).append(servicio)

        cierres = {
            (fila['equipo_id'], fila['servicio_plan_id']): fila['ultimo']
            for fila in OrdenTrabajo.objects.filter(
                equipo__in=equipos, estado=OrdenTrabajo.Estado.CERRADA, horometro_cierre__isnull=False
            ).values('equipo_id', 'servicio_plan_id').annotate(ultimo=Max('horometro_cierre'))
        }

        resultado = {}
        for equipo in equipos:
            mejor, mejor_horas = None, None
            for servicio in servicios_por_tipo.get(equipo.tipo_equipo_id, []):
                ultimo = cierres.get((equipo.id, servicio.id), Decimal('0.0'))
                horas = Decimal(servicio.intervalo_horas) - (equipo.horometro_actual - ultimo)
                if mejor_horas is None or horas < mejor_horas:
                    mejor, mejor_horas = servicio, horas
            resultado[equipo.id] = (mejor, mejor_horas)
        return resultado


def registrarCierreDeOrden(orden, valor, usuario):
    """Cierra la OT y deja la lectura del técnico en el historial del equipo.

    Cerrar es el momento en que el dato real entra al sistema: la máquina se
    intervino con ese horómetro, así que la lectura nace validada y con fuente
    TECNICO, que es de quien viene el dato. El horómetro del equipo se mueve con
    ella, para que la calculadora del próximo servicio lea el mismo número que
    quedó en el historial.
    """
    lectura = LecturaHorometro.objects.create(
        equipo=orden.equipo,
        usuario=usuario,
        valor=valor,
        fecha_hora=timezone.now(),
        fuente=LecturaHorometro.Fuente.TECNICO,
        validada=True,
        observacion=f'Cierre {orden.numero_ot}',
    )
    orden.cerrar(valor)
    orden.equipo.actualizarHorometro(valor)
    return lectura
