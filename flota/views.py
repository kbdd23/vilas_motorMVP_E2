from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from arriendos.models import Arriendo
from horometros.services import fuenteSugerida

from .forms import EquipoForm, TipoEquipoForm
from .models import Equipo, TipoEquipo


def lista_equipos(request):
    """Inventario de la flota: listado de equipos con su estado y horómetro.

    El desplegable de "Cambiar estado" sale de acá para que la pantalla y el modelo
    no puedan discrepar sobre qué estados existen.
    """
    equipos = Equipo.objects.select_related('tipo_equipo').order_by('codigo')
    return render(request, 'flota/equipos.html', {
        'equipos': equipos,
        'estados': Equipo.Estado.choices,
    })


def lista_tipos_equipo(request):
    """Categorías de equipos y su unidad de medida."""
    tipos = TipoEquipo.objects.order_by('nombre')
    return render(request, 'flota/tipos_equipo.html', {'tipos': tipos})


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
        'fuente_sugerida': fuenteSugerida(equipo),
    })


@login_required
@require_POST
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
