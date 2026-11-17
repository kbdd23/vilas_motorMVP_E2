"""Planilla de órdenes de trabajo: historial global de mantención."""

from vilas_motor.exportacion import (
    ajustar_anchos,
    escribir_encabezado,
    escribir_valores,
    libro_nuevo,
)

TITULOS_ORDENES = [
    'N° OT', 'Equipo', 'Tipo', 'Estado', 'Servicio',
    'Fecha programada', 'Fecha ejecución', 'Horómetro de cierre', 'Observaciones',
]

ANCHOS_ORDENES = [14, 16, 14, 14, 26, 18, 16, 20, 40]


def construir_libro_ordenes(ordenes):
    """Historial de órdenes de trabajo, en el orden en que llega el queryset."""
    libro, hoja = libro_nuevo('Órdenes de trabajo')
    escribir_encabezado(hoja, 1, TITULOS_ORDENES)

    fila = 2
    for orden in ordenes:
        escribir_valores(hoja, fila, [
            orden.numero_ot,
            orden.equipo.codigo,
            orden.get_tipo_display(),
            orden.get_estado_display(),
            orden.servicio_plan.nombre if orden.servicio_plan else '',
            orden.fecha_programada,
            orden.fecha_ejecucion,
            float(orden.horometro_cierre) if orden.horometro_cierre is not None else '',
            orden.observaciones or '',
        ])
        fila += 1

    ajustar_anchos(hoja, ANCHOS_ORDENES)
    hoja.freeze_panes = 'A2'
    return libro
