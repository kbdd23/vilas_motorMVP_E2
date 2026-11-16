"""Buscador global del panel: equipos, ordenes de trabajo y clientes.

La coincidencia es textual y la resuelve MySQL: la base declara el collation
utf8mb4_0900_ai_ci, que compara sin distinguir mayusculas ni tildes, asi que
"grua" encuentra "Grua" y "GRUA". Python solo puntua y ordena, normalizando por
su cuenta porque el interprete si distingue acentos.
"""

import unicodedata

from django.db.models import F, Q
from django.urls import reverse

from cuentas.models import Cliente
from flota.models import Equipo
from mantencion.models import OrdenTrabajo

MAXIMO_POR_CATEGORIA = 6
MAXIMO_CANDIDATOS = 40
LARGO_MINIMO = 2

# Palabras que, escritas solas, despliegan una categoria completa en vez de
# filtrar por texto. La comparacion es contra el token exacto, para que "otro"
# no active las ordenes de trabajo.
ALIAS_CATEGORIAS = {
    'OT': 'ordenes',
    'ORDEN': 'ordenes',
    'ORDENES': 'ordenes',
    'EQUIPO': 'equipos',
    'EQUIPOS': 'equipos',
    'MAQUINA': 'equipos',
    'CLIENTE': 'clientes',
    'CLIENTES': 'clientes',
}

# Cuando la busqueda no trae numero, manda la actividad mas reciente.
ORDEN_RECENCIA = (
    F('fecha_ejecucion').desc(nulls_last=True),
    F('fecha_programada').desc(nulls_last=True),
    '-id',
)


def normalizar(texto):
    """Pasa a minusculas y quita tildes, imitando al collation de MySQL."""
    descompuesto = unicodedata.normalize('NFKD', texto or '')
    return ''.join(
        caracter for caracter in descompuesto if not unicodedata.combining(caracter)
    ).lower()


def _puntaje(valores_principales, valores_secundarios, terminos):
    """Puntua un registro contra todos los terminos; devuelve 0 si alguno falla."""
    principales = [normalizar(valor) for valor in valores_principales if valor]
    secundarios = [normalizar(valor) for valor in valores_secundarios if valor]

    total = 0
    for termino in terminos:
        mejor = 0
        for valor in principales:
            if valor == termino:
                mejor = max(mejor, 100)
            elif valor.startswith(termino):
                mejor = max(mejor, 50)
            elif termino in valor:
                mejor = max(mejor, 10)
        if not mejor:
            for valor in secundarios:
                if termino in valor:
                    mejor = 1
                    break
        if not mejor:
            return 0
        total += mejor
    return total


def _filtro_equipos(terminos):
    filtro = Q()
    for termino in terminos:
        filtro &= (
            Q(codigo__icontains=termino)
            | Q(patente__icontains=termino)
            | Q(marca__icontains=termino)
            | Q(modelo__icontains=termino)
            | Q(numero_serie__icontains=termino)
            | Q(tipo_equipo__nombre__icontains=termino)
        )
    return filtro


def _filtro_ordenes(terminos):
    filtro = Q()
    for termino in terminos:
        filtro &= (
            Q(numero_ot__icontains=termino)
            | Q(observaciones__icontains=termino)
            | Q(equipo__codigo__icontains=termino)
            | Q(equipo__marca__icontains=termino)
            | Q(equipo__modelo__icontains=termino)
            | Q(servicio_plan__nombre__icontains=termino)
        )
    return filtro


def _filtro_clientes(terminos):
    filtro = Q()
    for termino in terminos:
        filtro &= (
            Q(rut__icontains=termino)
            | Q(razon_social__icontains=termino)
            | Q(email_contacto__icontains=termino)
            | Q(telefono__icontains=termino)
        )
    return filtro


def _resultado_equipo(equipo, terminos):
    detalle = ' · '.join(
        parte for parte in (equipo.tipo_equipo.nombre, equipo.marca, equipo.modelo) if parte
    )
    return {
        'categoria': 'Equipos',
        'titulo': equipo.codigo,
        'detalle': detalle,
        'url': reverse('flota:detalle_equipo', args=[equipo.id]),
        'puntaje': _puntaje(
            [
                equipo.codigo,
                equipo.marca,
                equipo.modelo,
                equipo.patente,
                equipo.numero_serie,
                equipo.tipo_equipo.nombre,
            ],
            [],
            terminos,
        ),
    }


def _resultado_orden(orden, terminos):
    equipo = orden.equipo
    fecha = orden.fecha_ejecucion or orden.fecha_programada
    detalle = ' · '.join(
        parte
        for parte in (equipo.codigo, orden.get_estado_display(), str(fecha) if fecha else '')
        if parte
    )
    return {
        'categoria': 'Órdenes de trabajo',
        'titulo': f'OT {orden.numero_ot}',
        'detalle': detalle,
        'url': reverse('mantencion:detalle_orden', args=[orden.id]),
        'puntaje': _puntaje(
            [orden.numero_ot, equipo.codigo, equipo.marca, equipo.modelo],
            [orden.observaciones],
            terminos,
        ),
    }


def _resultado_cliente(cliente, terminos):
    detalle = ' · '.join(
        parte
        for parte in (f'RUT {cliente.rut}', cliente.email_contacto, cliente.telefono)
        if parte
    )
    return {
        'categoria': 'Clientes',
        'titulo': cliente.razon_social,
        'detalle': detalle,
        'url': reverse('cuentas:clientes'),
        'puntaje': _puntaje(
            [cliente.razon_social, cliente.rut],
            [cliente.email_contacto],
            terminos,
        ),
    }


def _recortar(resultados, limite=MAXIMO_POR_CATEGORIA):
    """Sube las coincidencias exactas, respeta el orden recibido y recorta."""
    ordenados = sorted(
        enumerate(resultados), key=lambda par: (-par[1]['puntaje'], par[0])
    )
    seleccionados = []
    for _, resultado in ordenados[:limite]:
        seleccionados.append({
            clave: valor for clave, valor in resultado.items() if clave != 'puntaje'
        })
    return seleccionados


def _buscar_equipos(terminos):
    consulta = Equipo.objects.select_related('tipo_equipo')
    if terminos:
        consulta = consulta.filter(_filtro_equipos(terminos))
    candidatos = [
        _resultado_equipo(equipo, terminos)
        for equipo in consulta.order_by('codigo')[:MAXIMO_CANDIDATOS]
    ]
    return _recortar(candidatos)


def _buscar_ordenes(terminos):
    consulta = OrdenTrabajo.objects.select_related('equipo', 'servicio_plan')
    if terminos:
        consulta = consulta.filter(_filtro_ordenes(terminos))
    candidatos = [
        _resultado_orden(orden, terminos)
        for orden in consulta.order_by(*ORDEN_RECENCIA)[:MAXIMO_CANDIDATOS]
    ]
    return _recortar(candidatos)


def _buscar_clientes(terminos):
    consulta = Cliente.objects.all()
    if terminos:
        consulta = consulta.filter(_filtro_clientes(terminos))
    candidatos = [
        _resultado_cliente(cliente, terminos)
        for cliente in consulta.order_by('razon_social')[:MAXIMO_CANDIDATOS]
    ]
    return _recortar(candidatos)


def buscar_todo(texto):
    """Devuelve las coincidencias agrupadas por categoria, ya puntuadas."""
    consulta = (texto or '').strip()
    vacio = {'consulta': consulta, 'equipos': [], 'ordenes': [], 'clientes': [], 'total': 0}
    if len(consulta) < LARGO_MINIMO:
        return vacio

    tokens = consulta.split()
    categoria_forzada = ALIAS_CATEGORIAS.get(normalizar(tokens[0]).upper())
    if categoria_forzada:
        tokens = tokens[1:]
    terminos = [normalizar(token) for token in tokens]

    equipos = [] if categoria_forzada not in (None, 'equipos') else _buscar_equipos(terminos)
    ordenes = [] if categoria_forzada not in (None, 'ordenes') else _buscar_ordenes(terminos)
    clientes = [] if categoria_forzada not in (None, 'clientes') else _buscar_clientes(terminos)

    return {
        'consulta': consulta,
        'equipos': equipos,
        'ordenes': ordenes,
        'clientes': clientes,
        'total': len(equipos) + len(ordenes) + len(clientes),
    }
