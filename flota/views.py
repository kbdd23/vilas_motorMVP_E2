from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from arriendos.models import Arriendo
from cuentas.permisos import puedeExportar, puedeGestionar, requiere_rol_exportador, requiere_rol_gestion
from horometros.services import fuenteSugerida
from mantencion.models import PlanMantencion
from mantencion.services import pronosticoMantencion
from vilas_motor.exportacion import marca_de_tiempo, respuesta_excel

from .exportacion import construir_libro_flota, construir_libro_historial
from .forms import EquipoForm, TipoEquipoForm
from .models import Equipo, TipoEquipo


def lista_equipos(request):
    """Inventario de la flota: listado de equipos con su estado y horómetro.

    El desplegable de "Cambiar estado" sale de acá para que la pantalla y el modelo
    no puedan discrepar sobre qué estados existen.
    """
    estado = request.GET.get('estado')
    estados_validos = dict(Equipo.Estado.choices)
    equipos = Equipo.objects.select_related('tipo_equipo').order_by('codigo')
    if estado in estados_validos:
        equipos = equipos.filter(estado=estado)
    else:
        estado = None
    equipos = list(equipos)
    pronosticos = pronosticoMantencion(equipos)
    # Plan de mantención de cada tipo de equipo (el primero creado, si hay varios),
    # para el botón "Modificar mantención" de la columna Acción.
    plan_por_tipo = {}
    for plan in PlanMantencion.objects.filter(
        tipo_equipo__in={e.tipo_equipo_id for e in equipos}
    ).order_by('id'):
        plan_por_tipo.setdefault(plan.tipo_equipo_id, plan.id)
    for equipo in equipos:
        equipo.mantencion = pronosticos[equipo.id]
        equipo.plan_mantencion_id = plan_por_tipo.get(equipo.tipo_equipo_id)
    return render(request, 'flota/equipos.html', {
        'equipos': equipos,
        'estados': Equipo.Estado.choices,
        'estado_filtrado': estado,
        'etiqueta_estado_filtrado': estados_validos.get(estado),
        'puede_exportar': puedeExportar(request.user),
        'puede_gestionar': puedeGestionar(request.user),
    })


def lista_tipos_equipo(request):
    """Categorías de equipos y su unidad de medida."""
    tipos = TipoEquipo.objects.order_by('nombre')
    return render(request, 'flota/tipos_equipo.html', {'tipos': tipos})


@requiere_rol_gestion
def crear_tipo_equipo(request):
    """Crea una categoría de equipo."""
    if request.method == 'POST':
        form = TipoEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('flota:tipos_equipo')
    else:
        form = TipoEquipoForm()
    return render(request, 'flota/crear_tipo_equipo.html', {'form': form})


@requiere_rol_gestion
def crear_equipo(request):
    """Crea un equipo en el inventario."""
    if request.method == 'POST':
        form = EquipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('flota:equipos')
    else:
        form = EquipoForm()
    return render(request, 'flota/crear_equipo.html', {'form': form})


@requiere_rol_gestion
def editar_equipo(request, pk):
    """Edita los datos de un equipo ya registrado.

    El código no se edita: se asignó al crear la ficha, automático o manual.
    """
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == 'POST':
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            return redirect('flota:detalle_equipo', pk=equipo.pk)
    else:
        form = EquipoForm(instance=equipo)
    return render(request, 'flota/editar_equipo.html', {'form': form, 'equipo': equipo})


def detalle_equipo(request, pk):
    """Ficha del equipo con su historial de lecturas, OT y arriendos.

    El enlace para pedir el horómetro llega con la fuente ya elegida, porque el
    estado del equipo es el que dice a quién tiene sentido pedírselo.
    """
    equipo = get_object_or_404(
        Equipo.objects.select_related('tipo_equipo').prefetch_related(
            'lecturas', 'solicitudes_horometro', 'ordenes_trabajo', 'arriendos__cliente'
        ),
        pk=pk,
    )
    return render(request, 'flota/detalle_equipo.html', {
        'equipo': equipo,
        'mantencion': pronosticoMantencion([equipo])[equipo.id],
        'fuente_sugerida': fuenteSugerida(equipo),
        'puede_exportar': puedeExportar(request.user),
    })


@login_required
@require_POST
@requiere_rol_gestion
def marcar_disponible(request, pk):
    """Devuelve un equipo a disponible, una vez terminado su arriendo.

    Mientras el arriendo siga vigente la máquina está comprometida con el
    cliente, así que el estado no cambia.
    """
    equipo = get_object_or_404(Equipo, pk=pk)
    if not Arriendo.objects.vigentes().filter(equipo=equipo).exists():
        equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
    return redirect('arriendos:arriendos')


@login_required
@require_POST
@requiere_rol_gestion
def cambiar_estado(request, pk):
    """Cambia el estado de un equipo desde el inventario.

    Es la salida rápida para corregir a mano lo que el flujo no puede deducir: un
    equipo que quedó en faena, uno que vuelve del taller o uno que pasa a uso
    interno. Entrar a mantenimiento desde acá también recuerda de dónde se venía.
    """
    equipo = get_object_or_404(Equipo, pk=pk)
    try:
        equipo.cambiarEstado(request.POST.get('estado'))
    except ValueError:
        pass  # estado inválido: se ignora y la lista queda igual
    return redirect('flota:equipos')


@login_required
def posiciones_flota(request):
    """Posiciones para el mapa de flota en vivo del dashboard.

    Solo viajan los equipos con coordenadas; el resto se cuenta aparte para que
    el panel pueda decir cuántos faltan en vez de mostrar un mapa vacío sin
    explicación.
    """
    equipos = Equipo.objects.select_related('tipo_equipo')
    con_ubicacion = equipos.exclude(latitud__isnull=True).exclude(longitud__isnull=True)

    posiciones = []
    for equipo in con_ubicacion.order_by('codigo'):
        posiciones.append({
            'codigo': equipo.codigo,
            'lat': float(equipo.latitud),
            'lng': float(equipo.longitud),
            'estado': equipo.estado,
            'estado_etiqueta': equipo.get_estado_display(),
            'tipo': equipo.tipo_equipo.nombre,
            'marca': equipo.marca or '',
            'modelo': equipo.modelo or '',
            'patente': equipo.patente or '',
            'horometro': str(equipo.horometro_actual),
            'detalle': ' · '.join(
                parte
                for parte in (equipo.tipo_equipo.nombre, equipo.marca, equipo.modelo)
                if parte
            ),
            'senal': equipo.ultima_senal.isoformat() if equipo.ultima_senal else None,
            'url': reverse('flota:detalle_equipo', args=[equipo.id]),
        })

    return JsonResponse({
        'posiciones': posiciones,
        'total': len(posiciones),
        'sin_ubicacion': equipos.count() - len(posiciones),
        'generado': timezone.now().isoformat(),
    })


@login_required
@requiere_rol_exportador
def exportar_flota(request):
    """Descarga el inventario en Excel, con el mismo filtro de la pantalla.

    Si la lista está filtrada por estado, el archivo trae solo esos equipos: un
    export que ignora el filtro miente sobre lo que el usuario está viendo.
    """
    estado = request.GET.get('estado')
    equipos = Equipo.objects.select_related('tipo_equipo').order_by('codigo')

    if estado in dict(Equipo.Estado.choices):
        equipos = equipos.filter(estado=estado)
        sufijo = f'_{estado.lower()}'
    else:
        sufijo = ''

    libro = construir_libro_flota(equipos)
    return respuesta_excel(libro, f'flota{sufijo}_{marca_de_tiempo()}.xlsx')


@login_required
@requiere_rol_exportador
def exportar_historial_equipo(request, pk):
    """Descarga el historial de mantención de un equipo en el formato del taller."""
    equipo = get_object_or_404(Equipo.objects.select_related('tipo_equipo'), pk=pk)
    libro = construir_libro_historial(equipo)
    return respuesta_excel(libro, f'historial_{equipo.codigo}_{marca_de_tiempo()}.xlsx')
