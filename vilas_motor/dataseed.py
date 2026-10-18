"""Datos de demostración para Vilas Motor.

Carga un conjunto acotado y coherente de datos para poder recorrer la aplicación
sin depender del admin ni de la base real del cliente.

Procedencia de los valores:
    - Los marcados con el comentario "real" provienen de las planillas del
      levantamiento: PAUTA INSUMOS GENERADOR G45QX.xlsx y PLANILLA DE V168.xlsx.
    - El resto se infirió para que el sistema se vea en uso.

Regla de diseño: los clientes NO son usuarios. Viven únicamente en la tabla
'cliente'; todo lo que necesita un 'usuario' usa el planificador ya existente.

Uso:
    python manage.py seed_demo
    python manage.py seed_demo --flush
"""
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from arriendos.models import Arriendo
from auditoria.models import Auditoria
from cuentas.models import Cliente, Usuario
from flota.models import Equipo, TipoEquipo
from horometros.models import LecturaHorometro, SolicitudHorometro
from insumos.models import Insumo
from mantencion.models import (
    OrdenTrabajo,
    OrdenTrabajoInsumo,
    PlanMantencion,
    ServicioPlan,
    ServicioPlanInsumo,
)

# --- Clientes -----------------------------------------------------------------

CLIENTES = [
    {
        'rut': '76.543.210-K',
        'razon_social': 'Minera Cerro Dragón SpA',
        'email_contacto': 'contacto@cerrodragon.cl',
        'telefono': '+56 57 234 1100',
    },
    {
        'rut': '77.111.222-3',
        'razon_social': 'Constructora Altiplano Ltda',
        'email_contacto': 'obras@altiplano.cl',
        'telefono': '+56 57 241 8820',
    },
    {
        'rut': '78.222.333-4',
        'razon_social': 'Servicios Portuarios Iquique SpA',
        'email_contacto': 'admin@spi.cl',
        'telefono': '+56 57 251 3340',
    },
    {
        'rut': '79.333.444-5',
        'razon_social': 'Áridos del Norte Ltda',
        'email_contacto': 'ventas@aridosnorte.cl',
        'telefono': '+56 57 262 7710',
    },
    {
        'rut': '80.444.555-6',
        'razon_social': 'Logística Tarapacá SpA',
        'email_contacto': 'flota@logtarapaca.cl',
        'telefono': '+56 57 271 0099',
    },
]

# --- Catálogos de flota e insumos ---------------------------------------------

# Los tipos de equipo provienen del levantamiento (sección "Equipamiento").
TIPOS_EQUIPO = [
    ('Grúa horquilla', TipoEquipo.UnidadMedida.HORAS),
    ('Excavadora', TipoEquipo.UnidadMedida.HORAS),
    ('Retroexcavadora', TipoEquipo.UnidadMedida.HORAS),
    ('Generador', TipoEquipo.UnidadMedida.HORAS),
    ('Camión', TipoEquipo.UnidadMedida.KM),
]

# Los ocho insumos de la pauta del generador. El Excel no trae códigos:
# los asignamos nosotros para tener clave natural.
INSUMOS = [
    ('INS-001', 'ACEITE MOTOR 15W40 (Total Rubia Tir 7400)', 'LTS'),
    ('INS-002', 'FILTRO ACEITE DE MOTOR 02/971635', 'UN'),
    ('INS-003', 'FILTRO COMBUSTIBLE 02/971620', 'UN'),
    ('INS-004', 'FILTRO DE AIRE EXTERIOR 02/971664', 'UN'),
    ('INS-005', 'FILTRO DE AIRE INTERIOR', 'UN'),
    ('INS-006', 'LOGO ADHESIVO MANTENCION', 'UN'),
    ('INS-007', 'CORREA VENTILADOR JCB G45QX', 'UN'),
    ('INS-008', 'REFRIGERANTE', 'LTS'),
]

# --- Planes, servicios y recetas ----------------------------------------------
#
# La receta del generador es literal de la planilla "Base de datos". El bloque
# de insumos que quedaba suelto en el Excel se resolvió así: la correa del
# ventilador entra en el servicio de 500 horas, el filtro de aire interior en
# los de 1000 y 2000, y el refrigerante en el de 250.

PLANES = [
    {
        'nombre': 'Plan Generador G45QX',
        'tipo_equipo': 'Generador',
        'servicios': ['250 HORAS', '500 HORAS', '1000 HORAS', '2000 HORAS'],
        'receta': {
            '250 HORAS': {'INS-001': 11, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-006': 1, 'INS-008': 10},
            '500 HORAS': {'INS-001': 11, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-006': 1, 'INS-007': 1},
            '1000 HORAS': {'INS-001': 11, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-005': 1, 'INS-006': 1},
            '2000 HORAS': {'INS-001': 11, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-005': 1, 'INS-006': 1},
        },
    },
    {
        'nombre': 'Plan Grúa Horquilla',
        'tipo_equipo': 'Grúa horquilla',
        'servicios': ['250 HORAS', '500 HORAS', '1000 HORAS'],
        'receta': {
            '250 HORAS': {'INS-001': 8, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-006': 1},
            '500 HORAS': {'INS-001': 8, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-006': 1},
            '1000 HORAS': {'INS-001': 8, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-005': 1, 'INS-006': 1},
        },
    },
    {
        'nombre': 'Plan Excavadora',
        'tipo_equipo': 'Excavadora',
        'servicios': ['500 HORAS', '1000 HORAS'],
        'receta': {
            '500 HORAS': {'INS-001': 16, 'INS-002': 1, 'INS-003': 2, 'INS-004': 1},
            '1000 HORAS': {'INS-001': 16, 'INS-002': 1, 'INS-003': 2, 'INS-004': 1, 'INS-005': 1},
        },
    },
    {
        'nombre': 'Plan Retroexcavadora',
        'tipo_equipo': 'Retroexcavadora',
        'servicios': ['500 HORAS', '1000 HORAS'],
        'receta': {
            '500 HORAS': {'INS-001': 8, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1},
            '1000 HORAS': {'INS-001': 8, 'INS-002': 1, 'INS-003': 1, 'INS-004': 1, 'INS-005': 1},
        },
    },
    {
        'nombre': 'Plan Camión',
        'tipo_equipo': 'Camión',
        'servicios': ['10000 KM', '20000 KM'],
        'receta': {
            '10000 KM': {'INS-001': 24, 'INS-002': 1, 'INS-003': 2, 'INS-004': 1},
            '20000 KM': {'INS-001': 24, 'INS-002': 1, 'INS-003': 2, 'INS-004': 1, 'INS-005': 1},
        },
    },
]

# El nombre del servicio y su intervalo en la unidad del tipo de equipo.
INTERVALOS = {
    '250 HORAS': 250,
    '500 HORAS': 500,
    '1000 HORAS': 1000,
    '2000 HORAS': 2000,
    '10000 KM': 10000,
    '20000 KM': 20000,
}

# --- Equipos ------------------------------------------------------------------

EQUIPOS = [
    {
        # real: PLANILLA DE V168.xlsx (grúa horquilla 3.5 ton, PPU SVTJ39)
        'codigo': 'V168',
        'tipo_equipo': 'Grúa horquilla',
        'marca': 'Toyota',
        'modelo': '8FGU25',
        'patente': 'SVTJ39',
        'numero_serie': '8FGU25-V168',
        'estado': Equipo.Estado.EN_FAENA,
        'horometro_actual': Decimal('3620.0'),
    },
    {
        # real: PAUTA INSUMOS GENERADOR G45QX.xlsx (generador VG10-VG11)
        'codigo': 'G45QX',
        'tipo_equipo': 'Generador',
        'marca': 'JCB',
        'modelo': 'G45QX',
        'patente': None,
        'numero_serie': 'JCBG45QX-2023-018',
        'estado': Equipo.Estado.EN_FAENA,
        'horometro_actual': Decimal('480.0'),
    },
    {
        'codigo': 'EX-204',
        'tipo_equipo': 'Excavadora',
        'marca': 'Caterpillar',
        'modelo': '320',
        'patente': None,
        'numero_serie': 'CAT0320-EX204',
        'estado': Equipo.Estado.EN_MANTENIMIENTO,
        'horometro_actual': Decimal('3120.0'),
    },
    {
        'codigo': 'RET-118',
        'tipo_equipo': 'Retroexcavadora',
        'marca': 'JCB',
        'modelo': '3CX',
        'patente': None,
        'numero_serie': 'JCB3CX-RET118',
        'estado': Equipo.Estado.DISPONIBLE,
        'horometro_actual': Decimal('1450.5'),
    },
    {
        'codigo': 'CAM-301',
        'tipo_equipo': 'Camión',
        'marca': 'Mercedes-Benz',
        'modelo': 'Actros 2645',
        'patente': 'BJKT-45',
        'numero_serie': 'WDB9640-CAM301',
        'estado': Equipo.Estado.EN_FAENA,
        'horometro_actual': Decimal('128400.0'),
    },
]

# --- Lecturas de horómetro ----------------------------------------------------

# Cada equipo es una serie ascendente: el horómetro nunca retrocede. La primera
# lectura de cada equipo coincide con el cierre de su última orden de trabajo.
LECTURAS = [
    {'equipo': 'V168', 'momento': (2026, 8, 14, 17, 5), 'valor': Decimal('3500.0'),
     'fuente': LecturaHorometro.Fuente.TECNICO, 'validada': True},
    {'equipo': 'V168', 'momento': (2026, 9, 12, 8, 20), 'valor': Decimal('3560.5'),
     'fuente': LecturaHorometro.Fuente.CLIENTE, 'validada': True},
    {'equipo': 'V168', 'momento': (2026, 10, 6, 11, 0), 'valor': Decimal('3620.0'),
     'fuente': LecturaHorometro.Fuente.TELEMETRIA, 'validada': False},
    {'equipo': 'G45QX', 'momento': (2026, 2, 10, 9, 30), 'valor': Decimal('460.0'),
     'fuente': LecturaHorometro.Fuente.TECNICO, 'validada': True},
    {'equipo': 'G45QX', 'momento': (2026, 9, 28, 14, 45), 'valor': Decimal('480.0'),
     'fuente': LecturaHorometro.Fuente.PLANIFICACION, 'validada': True},
    {'equipo': 'EX-204', 'momento': (2026, 4, 7, 17, 30), 'valor': Decimal('2900.0'),
     'fuente': LecturaHorometro.Fuente.TECNICO, 'validada': True},
    {'equipo': 'EX-204', 'momento': (2026, 9, 19, 10, 0), 'valor': Decimal('3120.0'),
     'fuente': LecturaHorometro.Fuente.CLIENTE, 'validada': True},
    {'equipo': 'RET-118', 'momento': (2026, 5, 14, 16, 0), 'valor': Decimal('1400.0'),
     'fuente': LecturaHorometro.Fuente.TECNICO, 'validada': True},
    {'equipo': 'RET-118', 'momento': (2026, 8, 27, 9, 15), 'valor': Decimal('1450.5'),
     'fuente': LecturaHorometro.Fuente.PLANIFICACION, 'validada': True},
    {'equipo': 'CAM-301', 'momento': (2026, 6, 3, 18, 20), 'valor': Decimal('121000.0'),
     'fuente': LecturaHorometro.Fuente.TECNICO, 'validada': True},
    {'equipo': 'CAM-301', 'momento': (2026, 9, 30, 7, 40), 'valor': Decimal('128400.0'),
     'fuente': LecturaHorometro.Fuente.TELEMETRIA, 'validada': False},
]

# --- Solicitudes de horómetro -------------------------------------------------

# 'lectura' referencia la lectura que cumple la solicitud (por equipo y fecha).
SOLICITUDES = [
    {'equipo': 'V168', 'cliente': '76.543.210-K', 'momento': (2026, 9, 1, 9, 0),
     'estado': SolicitudHorometro.Estado.CUMPLIDA, 'lectura': ('V168', (2026, 9, 12, 8, 20))},
    {'equipo': 'G45QX', 'cliente': '79.333.444-5', 'momento': (2026, 9, 15, 10, 30),
     'estado': SolicitudHorometro.Estado.CUMPLIDA, 'lectura': ('G45QX', (2026, 9, 28, 14, 45))},
    {'equipo': 'EX-204', 'cliente': '77.111.222-3', 'momento': (2026, 9, 20, 12, 0),
     'estado': SolicitudHorometro.Estado.PENDIENTE, 'lectura': None},
    {'equipo': 'RET-118', 'cliente': '80.444.555-6', 'momento': (2026, 10, 1, 8, 45),
     'estado': SolicitudHorometro.Estado.PENDIENTE, 'lectura': None},
    {'equipo': 'CAM-301', 'cliente': '78.222.333-4', 'momento': (2026, 10, 5, 15, 15),
     'estado': SolicitudHorometro.Estado.PENDIENTE, 'lectura': None},
]

# --- Arriendos ----------------------------------------------------------------

# fecha_termino nula significa arriendo vigente.
ARRIENDOS = [
    {'equipo': 'V168', 'cliente': '76.543.210-K', 'inicio': (2024, 1, 15), 'termino': None},
    {'equipo': 'G45QX', 'cliente': '79.333.444-5', 'inicio': (2025, 3, 1), 'termino': (2026, 2, 28)},
    {'equipo': 'EX-204', 'cliente': '77.111.222-3', 'inicio': (2025, 6, 10), 'termino': None},
    {'equipo': 'RET-118', 'cliente': '80.444.555-6', 'inicio': (2026, 1, 5), 'termino': (2026, 6, 30)},
    {'equipo': 'CAM-301', 'cliente': '78.222.333-4', 'inicio': (2026, 2, 1), 'termino': None},
]

# --- Órdenes de trabajo -------------------------------------------------------

# Las cinco primeras son de la V168; las tres marcadas como "real" vienen de la
# planilla (los números de la columna FECHA venían como serial de Excel y se
# convirtieron a fecha). El resto del historial se inventó de forma coherente:
# cada servicio de cada plan tiene su último cierre, para que el cálculo del
# próximo servicio no arranque desde cero. La fecha de cierre es proporcional al
# horómetro, así que el historial es consistente con el desgaste del equipo.
ORDENES = [
    # Grúa horquilla V168 (horómetro 3620) -> próximo: 500 HORAS, 80 h restantes
    {'numero_ot': 'OT-100666', 'equipo': 'V168', 'servicio': '250 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2025, 6, 19), 'ejecucion': (2025, 6, 26), 'cierre': Decimal('2363.0')},
    {'numero_ot': 'OT-106948', 'equipo': 'V168', 'servicio': '1000 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 5, 20), 'ejecucion': (2026, 5, 29), 'cierre': Decimal('3157.0')},
    {'numero_ot': 'OT-107500', 'equipo': 'V168', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 4, 13), 'ejecucion': (2026, 4, 20), 'cierre': Decimal('3200.0')},
    {'numero_ot': 'OT-108210', 'equipo': 'V168', 'servicio': '250 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 8, 6), 'ejecucion': (2026, 8, 14), 'cierre': Decimal('3500.0')},
    {'numero_ot': 'OT-109115', 'equipo': 'V168', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.PROGRAMADA,
     'programada': (2026, 11, 10), 'ejecucion': None, 'cierre': None},

    # Generador G45QX (horómetro 480) -> próximo: 250 HORAS, 100 h restantes
    {'numero_ot': 'OT-090014', 'equipo': 'G45QX', 'servicio': '2000 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2024, 2, 13), 'ejecucion': (2024, 2, 20), 'cierre': Decimal('50.0')},
    {'numero_ot': 'OT-091220', 'equipo': 'G45QX', 'servicio': '1000 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2024, 5, 8), 'ejecucion': (2024, 5, 15), 'cierre': Decimal('100.0')},
    {'numero_ot': 'OT-094830', 'equipo': 'G45QX', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2024, 10, 1), 'ejecucion': (2024, 10, 8), 'cierre': Decimal('200.0')},
    {'numero_ot': 'OT-099105', 'equipo': 'G45QX', 'servicio': '250 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2025, 6, 5), 'ejecucion': (2025, 6, 12), 'cierre': Decimal('330.0')},

    # Excavadora EX-204 (horómetro 3120) -> próximo: 500 HORAS, 280 h restantes
    {'numero_ot': 'OT-101338', 'equipo': 'EX-204', 'servicio': '1000 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2025, 9, 11), 'ejecucion': (2025, 9, 18), 'cierre': Decimal('2600.0')},
    {'numero_ot': 'OT-107190', 'equipo': 'EX-204', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 3, 31), 'ejecucion': (2026, 4, 7), 'cierre': Decimal('2900.0')},
    {'numero_ot': 'OT-109240', 'equipo': 'EX-204', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.EN_CURSO,
     'programada': (2026, 10, 5), 'ejecucion': None, 'cierre': None},

    # Retroexcavadora RET-118 (horómetro 1450.5) -> próximo: 500 HORAS, 449.5 restantes
    {'numero_ot': 'OT-100412', 'equipo': 'RET-118', 'servicio': '1000 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2025, 7, 15), 'ejecucion': (2025, 7, 22), 'cierre': Decimal('1000.0')},
    {'numero_ot': 'OT-108020', 'equipo': 'RET-118', 'servicio': '500 HORAS',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 5, 7), 'ejecucion': (2026, 5, 14), 'cierre': Decimal('1400.0')},

    # Camión CAM-301 (horómetro 128400) -> próximo: 20000 KM, 1600 restantes
    {'numero_ot': 'OT-101190', 'equipo': 'CAM-301', 'servicio': '20000 KM',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2025, 8, 4), 'ejecucion': (2025, 8, 11), 'cierre': Decimal('110000.0')},
    {'numero_ot': 'OT-108870', 'equipo': 'CAM-301', 'servicio': '10000 KM',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.CERRADA,
     'programada': (2026, 5, 27), 'ejecucion': (2026, 6, 3), 'cierre': Decimal('121000.0')},
    {'numero_ot': 'OT-109310', 'equipo': 'CAM-301', 'servicio': '10000 KM',
     'tipo': OrdenTrabajo.Tipo.PREVENTIVA, 'estado': OrdenTrabajo.Estado.PROGRAMADA,
     'programada': (2026, 11, 24), 'ejecucion': None, 'cierre': None},
]

# --- Auditoría ----------------------------------------------------------------

# Se siembran al final, cuando ya existen los registros referenciados, para
# guardar el id real en la referencia genérica.
AUDITORIAS = [
    {'entidad': 'orden_trabajo', 'operacion': Auditoria.Operacion.UPDATE,
     'momento': (2026, 8, 14, 17, 10), 'ip': '10.0.0.24',
     'valor_anterior': {'estado': 'PROGRAMADA'}, 'valor_nuevo': {'estado': 'CERRADA'}},
    {'entidad': 'solicitud_horometro', 'operacion': Auditoria.Operacion.INSERT,
     'momento': (2026, 9, 1, 9, 5), 'ip': '10.0.0.24',
     'valor_anterior': None, 'valor_nuevo': {'estado': 'PENDIENTE'}},
    {'entidad': 'lectura_horometro', 'operacion': Auditoria.Operacion.INSERT,
     'momento': (2026, 9, 12, 8, 25), 'ip': '10.0.0.31',
     'valor_anterior': None, 'valor_nuevo': {'valor': '3560.5', 'fuente': 'CLIENTE'}},
    {'entidad': 'arriendo', 'operacion': Auditoria.Operacion.INSERT,
     'momento': (2026, 2, 1, 12, 0), 'ip': '10.0.0.24',
     'valor_anterior': None, 'valor_nuevo': {'equipo': 'CAM-301', 'vigente': True}},
    {'entidad': 'lectura_horometro', 'operacion': Auditoria.Operacion.INSERT,
     'momento': (2026, 10, 6, 11, 2), 'ip': '10.0.0.31',
     'valor_anterior': None, 'valor_nuevo': {'valor': '3620.0', 'fuente': 'TELEMETRIA'}},
]


# --- Utilidades ---------------------------------------------------------------

def _momento(anio, mes, dia, hora=0, minuto=0):
    """Construye una fecha-hora consciente de zona horaria (USE_TZ = True)."""
    return timezone.make_aware(datetime(anio, mes, dia, hora, minuto))


def _fecha(anio, mes, dia):
    """Construye una fecha simple para los campos DateField."""
    return date(anio, mes, dia)


def _cantidad(valor):
    """Convierte a Decimal el valor de una receta o de un consumo."""
    return Decimal(str(valor))


# --- Limpieza -----------------------------------------------------------------

def limpiar():
    """Elimina solo los registros que este módulo crea, en orden inverso a las FK."""
    ordenes = [datos['numero_ot'] for datos in ORDENES]
    equipos = [datos['codigo'] for datos in EQUIPOS]
    planes = [datos['nombre'] for datos in PLANES]
    insumos = [codigo for codigo, _, _ in INSUMOS]
    tipos = [nombre for nombre, _ in TIPOS_EQUIPO]
    clientes = [datos['rut'] for datos in CLIENTES]

    OrdenTrabajoInsumo.objects.filter(orden_trabajo__numero_ot__in=ordenes).delete()
    OrdenTrabajo.objects.filter(numero_ot__in=ordenes).delete()
    SolicitudHorometro.objects.filter(equipo__codigo__in=equipos).delete()
    LecturaHorometro.objects.filter(equipo__codigo__in=equipos).delete()
    Arriendo.objects.filter(equipo__codigo__in=equipos).delete()
    Equipo.objects.filter(codigo__in=equipos).delete()
    ServicioPlanInsumo.objects.filter(servicio_plan__plan__nombre__in=planes).delete()
    ServicioPlan.objects.filter(plan__nombre__in=planes).delete()
    PlanMantencion.objects.filter(nombre__in=planes).delete()
    Insumo.objects.filter(codigo__in=insumos).delete()
    TipoEquipo.objects.filter(nombre__in=tipos).delete()
    Cliente.objects.filter(rut__in=clientes).delete()
    Auditoria.objects.filter(entidad__in=[datos['entidad'] for datos in AUDITORIAS]).delete()


# --- Bloques de carga ---------------------------------------------------------

def _obtener_planificador():
    """Devuelve el planificador ya existente: el seed no crea usuarios."""
    usuario = Usuario.objects.filter(rol__nombre='planificador').order_by('id').first()
    if usuario is None:
        raise RuntimeError(
            'No existe ningún usuario con rol planificador. '
            'Ejecuta las migraciones y crea el superusuario antes del seed.'
        )
    return usuario


def _sembrar_clientes():
    resultado = {}
    for datos in CLIENTES:
        cliente, _ = Cliente.objects.get_or_create(
            rut=datos['rut'],
            defaults={
                'razon_social': datos['razon_social'],
                'email_contacto': datos['email_contacto'],
                'telefono': datos['telefono'],
            },
        )
        resultado[datos['rut']] = cliente
    return resultado


def _sembrar_tipos_equipo():
    resultado = {}
    for nombre, unidad in TIPOS_EQUIPO:
        tipo, _ = TipoEquipo.objects.get_or_create(
            nombre=nombre,
            defaults={'unidad_medida': unidad},
        )
        resultado[nombre] = tipo
    return resultado


def _sembrar_insumos():
    resultado = {}
    for codigo, nombre, unidad in INSUMOS:
        insumo, _ = Insumo.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'unidad_medida': unidad},
        )
        resultado[codigo] = insumo
    return resultado


def _sembrar_planes(tipos, insumos):
    """Crea planes, servicios y las recetas de insumos de cada servicio."""
    resultado = {}
    for datos in PLANES:
        plan, _ = PlanMantencion.objects.get_or_create(
            nombre=datos['nombre'],
            defaults={'tipo_equipo': tipos[datos['tipo_equipo']]},
        )
        servicios = {}
        for nombre_servicio in datos['servicios']:
            servicio, _ = ServicioPlan.objects.get_or_create(
                plan=plan,
                nombre=nombre_servicio,
                defaults={'intervalo_horas': INTERVALOS[nombre_servicio]},
            )
            servicios[nombre_servicio] = servicio
            for codigo, cantidad in datos['receta'][nombre_servicio].items():
                ServicioPlanInsumo.objects.get_or_create(
                    servicio_plan=servicio,
                    insumo=insumos[codigo],
                    defaults={'cantidad': _cantidad(cantidad)},
                )
        resultado[datos['nombre']] = {
            'plan': plan,
            'servicios': servicios,
            'receta': datos['receta'],
        }
    return resultado


def _sembrar_equipos(tipos):
    resultado = {}
    for datos in EQUIPOS:
        equipo, _ = Equipo.objects.get_or_create(
            codigo=datos['codigo'],
            defaults={
                'tipo_equipo': tipos[datos['tipo_equipo']],
                'marca': datos['marca'],
                'modelo': datos['modelo'],
                'patente': datos['patente'],
                'numero_serie': datos['numero_serie'],
                'estado': datos['estado'],
                'horometro_actual': datos['horometro_actual'],
            },
        )
        resultado[datos['codigo']] = equipo
    return resultado


def _sembrar_lecturas(equipos, planificador):
    resultado = {}
    for datos in LECTURAS:
        momento = _momento(*datos['momento'])
        lectura, _ = LecturaHorometro.objects.get_or_create(
            equipo=equipos[datos['equipo']],
            fecha_hora=momento,
            defaults={
                'usuario': planificador,
                'valor': datos['valor'],
                'fuente': datos['fuente'],
                'validada': datos['validada'],
            },
        )
        resultado[(datos['equipo'], momento)] = lectura
    return resultado


def _sembrar_solicitudes(equipos, clientes, planificador, lecturas):
    resultado = []
    for datos in SOLICITUDES:
        lectura = None
        if datos['lectura'] is not None:
            equipo_lectura, momento_lectura = datos['lectura']
            lectura = lecturas[(equipo_lectura, _momento(*momento_lectura))]
        solicitud, _ = SolicitudHorometro.objects.get_or_create(
            equipo=equipos[datos['equipo']],
            fecha_solicitud=_momento(*datos['momento']),
            defaults={
                'cliente': clientes[datos['cliente']],
                'usuario_solicita': planificador,
                'estado': datos['estado'],
                'lectura': lectura,
            },
        )
        resultado.append(solicitud)
    return resultado


def _sembrar_arriendos(equipos, clientes):
    resultado = []
    for datos in ARRIENDOS:
        termino = _fecha(*datos['termino']) if datos['termino'] else None
        arriendo, _ = Arriendo.objects.get_or_create(
            equipo=equipos[datos['equipo']],
            fecha_inicio=_fecha(*datos['inicio']),
            defaults={
                'cliente': clientes[datos['cliente']],
                'fecha_termino': termino,
            },
        )
        resultado.append(arriendo)
    return resultado


def _plan_del_equipo(planes, equipo):
    """Devuelve el bloque del plan cuyo tipo de equipo corresponde al del equipo."""
    for bloque in planes.values():
        if bloque['plan'].tipo_equipo_id == equipo.tipo_equipo_id:
            return bloque
    raise RuntimeError(f'El equipo {equipo.codigo} no tiene un plan de mantención asociado.')


def _sembrar_ordenes(equipos, planes, insumos):
    """Crea las OT y les asocia los insumos que indica la receta del servicio."""
    resultado = []
    for datos in ORDENES:
        equipo = equipos[datos['equipo']]
        bloque = _plan_del_equipo(planes, equipo)
        orden, _ = OrdenTrabajo.objects.get_or_create(
            numero_ot=datos['numero_ot'],
            defaults={
                'equipo': equipo,
                'servicio_plan': bloque['servicios'][datos['servicio']],
                'tipo': datos['tipo'],
                'estado': datos['estado'],
                'fecha_programada': _fecha(*datos['programada']),
                'fecha_ejecucion': _fecha(*datos['ejecucion']) if datos['ejecucion'] else None,
                'horometro_cierre': datos['cierre'],
            },
        )
        if orden.estado == OrdenTrabajo.Estado.CERRADA:
            for codigo, cantidad in bloque['receta'][datos['servicio']].items():
                OrdenTrabajoInsumo.objects.get_or_create(
                    orden_trabajo=orden,
                    insumo=insumos[codigo],
                    defaults={'cantidad_usada': _cantidad(cantidad)},
                )
        resultado.append(orden)
    return resultado


def _sembrar_auditoria(planificador, ordenes, lecturas, solicitudes, arriendos):
    """Registra los eventos de auditoría apuntando a los ids recién creados."""
    referencias = {
        'orden_trabajo': next(o for o in ordenes if o.numero_ot == 'OT-108210').id,
        'solicitud_horometro': next(s for s in solicitudes if s.equipo.codigo == 'V168').id,
        'lectura_horometro': lecturas[('V168', _momento(2026, 9, 12, 8, 20))].id,
        'arriendo': next(a for a in arriendos if a.equipo.codigo == 'CAM-301').id,
    }
    resultado = []
    for datos in AUDITORIAS:
        momento = _momento(*datos['momento'])
        auditoria, _ = Auditoria.objects.get_or_create(
            usuario=planificador,
            fecha_hora=momento,
            entidad=datos['entidad'],
            id_registro=referencias[datos['entidad']],
            operacion=datos['operacion'],
            defaults={
                'valor_anterior': datos['valor_anterior'],
                'valor_nuevo': datos['valor_nuevo'],
                'ip': datos['ip'],
            },
        )
        resultado.append(auditoria)
    return resultado


# --- Punto de entrada ---------------------------------------------------------

@transaction.atomic
def sembrar(flush=False):
    """Carga el dataset de demostración y devuelve un resumen por tabla.

    Es idempotente: usa get_or_create sobre claves naturales, así que correrlo
    dos veces no duplica registros. Con flush=True elimina antes lo que este
    módulo creó.
    """
    if flush:
        limpiar()

    planificador = _obtener_planificador()
    clientes = _sembrar_clientes()
    tipos = _sembrar_tipos_equipo()
    insumos = _sembrar_insumos()
    planes = _sembrar_planes(tipos, insumos)
    equipos = _sembrar_equipos(tipos)
    lecturas = _sembrar_lecturas(equipos, planificador)
    solicitudes = _sembrar_solicitudes(equipos, clientes, planificador, lecturas)
    arriendos = _sembrar_arriendos(equipos, clientes)
    ordenes = _sembrar_ordenes(equipos, planes, insumos)
    _sembrar_auditoria(planificador, ordenes, lecturas, solicitudes, arriendos)

    return {
        'cliente': Cliente.objects.filter(rut__in=[d['rut'] for d in CLIENTES]).count(),
        'tipo_equipo': TipoEquipo.objects.filter(nombre__in=[n for n, _ in TIPOS_EQUIPO]).count(),
        'insumo': Insumo.objects.filter(codigo__in=[c for c, _, _ in INSUMOS]).count(),
        'plan_mantencion': PlanMantencion.objects.filter(nombre__in=[d['nombre'] for d in PLANES]).count(),
        'servicio_plan': ServicioPlan.objects.filter(plan__nombre__in=[d['nombre'] for d in PLANES]).count(),
        'servicio_plan_insumo': ServicioPlanInsumo.objects.filter(
            servicio_plan__plan__nombre__in=[d['nombre'] for d in PLANES]).count(),
        'equipo': Equipo.objects.filter(codigo__in=[d['codigo'] for d in EQUIPOS]).count(),
        'lectura_horometro': LecturaHorometro.objects.filter(
            equipo__codigo__in=[d['codigo'] for d in EQUIPOS]).count(),
        'solicitud_horometro': len(solicitudes),
        'arriendo': len(arriendos),
        'orden_trabajo': len(ordenes),
        'orden_trabajo_insumo': OrdenTrabajoInsumo.objects.filter(
            orden_trabajo__numero_ot__in=[d['numero_ot'] for d in ORDENES]).count(),
        'auditoria': len([d for d in AUDITORIAS]),
    }
