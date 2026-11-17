"""Planillas de flota: inventario completo e historial de un equipo."""

from vilas_motor.exportacion import (
    NEGRITA,
    ajustar_anchos,
    escribir_encabezado,
    escribir_valores,
    libro_nuevo,
)

TITULOS_FLOTA = [
    'Código', 'Tipo', 'Marca', 'Modelo', 'Patente',
    'N° de serie', 'Estado', 'Horómetro', 'Última señal',
]

ANCHOS_FLOTA = [16, 22, 16, 18, 12, 18, 18, 12, 18]

TITULOS_HISTORIAL = ['N°', 'OT', 'FECHA', 'MANTENIMIENTO', 'HORÓMETRO/KILOMETRAJE']

ANCHOS_HISTORIAL = [6, 14, 16, 24, 22]


def _descripcion_equipo(equipo):
    """Arma la línea que identifica la máquina bajo el título de la planilla."""
    partes = [equipo.tipo_equipo.nombre]
    if equipo.marca or equipo.modelo:
        partes.append(' '.join(filter(None, [equipo.marca, equipo.modelo])))
    if equipo.patente:
        partes.append(f'PPU {equipo.patente}')
    return ' - '.join(partes)


def _texto_mantenimiento(orden):
    """Traduce el servicio de la OT al texto de la planilla: "250 HORAS"."""
    servicio = orden.servicio_plan
    if servicio and servicio.intervalo_horas:
        return f'{servicio.intervalo_horas} HORAS'
    if servicio:
        return servicio.nombre
    return orden.get_tipo_display()


def construir_libro_flota(equipos):
    """Inventario de equipos, con el mismo criterio de orden que la pantalla."""
    libro, hoja = libro_nuevo('Flota')
    escribir_encabezado(hoja, 1, TITULOS_FLOTA)

    fila = 2
    for equipo in equipos:
        escribir_valores(hoja, fila, [
            equipo.codigo,
            equipo.tipo_equipo.nombre,
            equipo.marca or '',
            equipo.modelo or '',
            equipo.patente or '',
            equipo.numero_serie or '',
            equipo.get_estado_display(),
            float(equipo.horometro_actual),
            equipo.ultima_senal,
        ])
        fila += 1

    ajustar_anchos(hoja, ANCHOS_FLOTA)
    hoja.freeze_panes = 'A2'
    return libro


def construir_libro_historial(equipo):
    """Historial de un equipo con el formato de la planilla de mantención.

    Replica el encabezado del documento que usa el taller: sistema, servicio,
    número de equipo y descripción de la máquina, y luego la tabla de OT.
    """
    libro, hoja = libro_nuevo('HOJA 1')

    hoja['A1'] = 'SISTEMA DE GESTIÓN'
    hoja['A1'].font = NEGRITA
    hoja['A2'] = 'MANTENCIONES'
    hoja['A3'] = 'SERVICIO MANTENCIÓN'
    hoja['A4'] = f'N° DE EQUIPO: {equipo.codigo}'
    hoja['A4'].font = NEGRITA
    hoja['A5'] = _descripcion_equipo(equipo)
    hoja['A7'] = f'Código: {equipo.codigo}'
    hoja['A8'] = 'Rev: 01'

    escribir_encabezado(hoja, 10, TITULOS_HISTORIAL)

    ordenes = equipo.ordenes_trabajo.select_related('servicio_plan').order_by(
        'fecha_ejecucion', 'fecha_programada', 'id'
    )

    fila = 11
    for numero, orden in enumerate(ordenes, start=1):
        fecha = orden.fecha_ejecucion or orden.fecha_programada
        escribir_valores(hoja, fila, [
            numero,
            orden.numero_ot,
            fecha,
            _texto_mantenimiento(orden),
            float(orden.horometro_cierre) if orden.horometro_cierre is not None else '',
        ])
        fila += 1

    ajustar_anchos(hoja, ANCHOS_HISTORIAL)
    return libro
