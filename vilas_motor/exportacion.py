"""Utilidades para generar planillas Excel de exportación.

Todo se arma en memoria y se devuelve como descarga: son cientos de filas, así
que no hay razón para escribir archivos en el servidor.
"""

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

TIPO_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

_LADO = Side(style='thin', color='B0B0B0')
BORDE = Border(left=_LADO, right=_LADO, top=_LADO, bottom=_LADO)
NEGRITA = Font(bold=True)
RELLENO_ENCABEZADO = PatternFill('solid', fgColor='E9E9E9')
CENTRADO = Alignment(horizontal='center', vertical='center')
FORMATO_FECHA = 'DD-MM-YYYY'
FORMATO_NUMERO = '#,##0.0'


def libro_nuevo(titulo):
    """Crea un libro con una sola hoja ya nombrada."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo
    return libro, hoja


def escribir_encabezado(hoja, fila, titulos):
    """Escribe la fila de títulos de la tabla, con relleno y bordes."""
    for columna, titulo in enumerate(titulos, start=1):
        celda = hoja.cell(row=fila, column=columna, value=titulo)
        celda.font = NEGRITA
        celda.fill = RELLENO_ENCABEZADO
        celda.border = BORDE
        celda.alignment = CENTRADO


def _valor_para_excel(valor):
    """openpyxl rechaza fechas con zona horaria; Excel solo entiende hora local.

    Con USE_TZ activo, MySQL devuelve los datetime con tzinfo, así que se pasan a
    la zona del proyecto antes de escribir la celda.
    """
    if hasattr(valor, 'tzinfo') and valor.tzinfo is not None:
        return timezone.make_naive(valor, timezone.get_current_timezone())
    return valor


def escribir_valores(hoja, fila, valores):
    """Escribe una fila de datos y aplica bordes a cada celda."""
    for columna, valor in enumerate(valores, start=1):
        celda = hoja.cell(row=fila, column=columna, value=_valor_para_excel(valor))
        celda.border = BORDE
        if hasattr(valor, 'hour'):
            celda.number_format = 'DD-MM-YYYY HH:MM'
        elif hasattr(valor, 'year'):
            celda.number_format = FORMATO_FECHA
        elif isinstance(valor, float):
            celda.number_format = FORMATO_NUMERO


def ajustar_anchos(hoja, anchos):
    """Fija el ancho de cada columna a partir de una lista de medidas."""
    for indice, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho


def respuesta_excel(libro, nombre_archivo):
    """Devuelve el libro como descarga adjunta."""
    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    respuesta = HttpResponse(buffer.getvalue(), content_type=TIPO_XLSX)
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return respuesta


def marca_de_tiempo():
    """Fecha de hoy para nombrar el archivo."""
    return timezone.localdate().isoformat()
