"""Lectura de la planilla de maquinarias de la empresa (Equipos.xlsx).

La planilla trae MAQUINARIA, FABRICANTE, MODELO, N° INTERNO y PPU. La columna
MAQUINARIA mezcla el tipo con su capacidad ("GRUA HORQUILLA 7 TON", "GENERADOR
45 KVA"): aquí se separa en un tipo de equipo del sistema y un detalle que se
guarda junto al modelo. Sin N° interno, el código se arma con el prefijo del
tipo y un correlativo (GH-001, GEN-001...).
"""
import re
import unicodedata

# (palabras con que empieza MAQUINARIA, tipo de equipo, unidad, prefijo del código)
# El orden importa: lo más específico va primero ("CAMION PLUMA" antes que "CAMION").
TIPOS = [
    ('GRUA HORQUILLA', 'Grúa horquilla', 'HORAS', 'GH'),
    ('GRUA HORQULLA', 'Grúa horquilla', 'HORAS', 'GH'),
    ('GENERADOR', 'Generador', 'HORAS', 'GEN'),
    ('LUMINARIA', 'Luminaria', 'HORAS', 'LUM'),
    ('CAMIONETA', 'Camioneta', 'KM', 'CTA'),
    ('CAMION PLUMA', 'Camión pluma', 'KM', 'CPL'),
    ('CAMION TOLVA', 'Camión tolva', 'KM', 'CTO'),
    ('CAMION ALJIBE', 'Camión aljibe', 'KM', 'CAL'),
    ('TRACTO CAMION', 'Tracto camión', 'KM', 'TRC'),
    ('CAMION', 'Camión', 'KM', 'CAM'),
    ('CAMA BAJA', 'Remolque', 'KM', 'REM'),
    ('SEMIREMOLQUE', 'Remolque', 'KM', 'REM'),
    ('RAMPLA', 'Remolque', 'KM', 'REM'),
    ('RETRO EXCAVADORA', 'Retroexcavadora', 'HORAS', 'RET'),
    ('RETROEXCAVADORA', 'Retroexcavadora', 'HORAS', 'RET'),
    ('EXCAVADORA', 'Excavadora', 'HORAS', 'EXC'),
    ('PLUMA', 'Grúa pluma', 'HORAS', 'PLU'),
    ('COMPRESOR', 'Compresor', 'HORAS', 'COM'),
    ('MANIPULADOR', 'Manipulador telescópico', 'HORAS', 'MAN'),
    ('MINICARGADOR', 'Minicargador', 'HORAS', 'MIN'),
    ('CARGADOR FRONTAL', 'Cargador frontal', 'HORAS', 'CFR'),
    ('SOLDADORA', 'Soldadora', 'HORAS', 'SOL'),
    ('ALZA HOMBRE', 'Alza hombre', 'HORAS', 'AHO'),
    ('PLATAFORMA TIJERAS', 'Plataforma tijera', 'HORAS', 'PTI'),
    ('PLATAFORMA TIJERA', 'Plataforma tijera', 'HORAS', 'PTI'),
    ('RODILLO COMPACTADOR', 'Rodillo compactador', 'HORAS', 'ROD'),
    ('MOTONIVELADORA', 'Motoniveladora', 'HORAS', 'MOT'),
    ('MINIBUS', 'Minibús', 'KM', 'MBU'),
    ('FURGON', 'Furgón', 'KM', 'FUR'),
]


def _sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def _limpiar(valor):
    if valor is None:
        return ''
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r'\s+', ' ', str(valor)).strip()


def clasificar(maquinaria):
    """Devuelve (tipo, unidad, prefijo, detalle) para el texto de MAQUINARIA."""
    texto = _sin_tildes(_limpiar(maquinaria).upper())
    for inicio, tipo, unidad, prefijo in TIPOS:
        if texto.startswith(inicio):
            if inicio in ('CAMA BAJA', 'SEMIREMOLQUE', 'RAMPLA'):
                detalle = inicio  # el subtipo de remolque
            else:
                detalle = texto[len(inicio):].strip(' -')
            # "03 TON" -> "3 TON", "3TON" -> "3 TON"
            detalle = re.sub(r'\b0+(\d)', r'\1', detalle)
            detalle = re.sub(r'(\d)(TON|TN|KVA|M)\b', r'\1 \2', detalle)
            return tipo, unidad, prefijo, detalle
    raise ValueError(f'Maquinaria sin tipo conocido: "{maquinaria}"')


def leer_planilla(ruta):
    """Lee Equipos.xlsx y devuelve una lista de dicts listos para crear Equipo."""
    from openpyxl import load_workbook

    hoja = load_workbook(ruta, read_only=True, data_only=True).active
    filas = hoja.iter_rows(values_only=True)
    encabezado = [_sin_tildes(_limpiar(c).upper()) for c in next(filas)]
    columna = {nombre: i for i, nombre in enumerate(encabezado)}
    for requerida in ('MAQUINARIA', 'FABRICANTE', 'MODELO'):
        if requerida not in columna:
            raise ValueError(f'La planilla no tiene la columna {requerida}.')
    i_interno = next((i for n, i in columna.items() if n.startswith('N') and 'INTERNO' in n), None)
    i_ppu = columna.get('PPU')

    correlativos = {}
    equipos = []
    for numero, fila in enumerate(filas, start=2):
        maquinaria = _limpiar(fila[columna['MAQUINARIA']])
        if not maquinaria:
            continue
        tipo, unidad, prefijo, detalle = clasificar(maquinaria)
        modelo = _limpiar(fila[columna['MODELO']])
        if detalle:
            modelo = f'{modelo} ({detalle})' if modelo else detalle
        interno = _limpiar(fila[i_interno]) if i_interno is not None else ''
        if interno:
            codigo = interno.upper()
        else:
            correlativos[prefijo] = correlativos.get(prefijo, 0) + 1
            codigo = f'{prefijo}-{correlativos[prefijo]:03d}'
        equipos.append({
            'fila': numero,
            'codigo': codigo,
            'tipo_equipo': tipo,
            'unidad_medida': unidad,
            'marca': _limpiar(fila[columna['FABRICANTE']])[:50] or None,
            'modelo': modelo[:50] or None,
            'patente': (_limpiar(fila[i_ppu]).upper()[:10] or None) if i_ppu is not None else None,
        })
    return equipos
