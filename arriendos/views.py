from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from flota.models import Equipo
from flota.services import ESTADOS_SIN_DEVOLVER
from vilas_motor.ventanas import VENTANA_POR_DEFECTO, VENTANAS, dias_de_ventana

from .forms import ArriendoForm, CerrarArriendoForm
from .models import Arriendo


def lista_arriendos(request):
    """Bandeja de arriendos: todo contrato que tenga un paso pendiente.

    Un arriendo se termina en dos pasos: cerrar el contrato y marcar el regreso
    del equipo. Mientras falte cualquiera de los dos el contrato sigue en la
    bandeja, sin importar cuánto tiempo pase; un cierre sin regreso marcado no
    se limpia nunca. La ventana gobierna solo los contratos ya resueltos, para
    que el cierre del día se alcance a ver.

    Se muestra una fila por equipo: la de su contrato más reciente.
    """
    clave_ventana = request.GET.get('ventana', VENTANA_POR_DEFECTO)
    limite = timezone.localdate() - timedelta(days=dias_de_ventana(clave_ventana))

    candidatos = (
        Arriendo.objects.select_related('equipo', 'cliente')
        .filter(
            Q(fecha_termino__isnull=True)
            | Q(equipo__estado__in=ESTADOS_SIN_DEVOLVER)
            | Q(fecha_termino__gte=limite)
        )
        .order_by('-fecha_inicio', '-id')
    )

    arriendos = []
    equipos_vistos = set()
    for arriendo in candidatos:
        if arriendo.equipo_id not in equipos_vistos:
            equipos_vistos.add(arriendo.equipo_id)
            arriendos.append(arriendo)

    return render(request, 'arriendos/arriendos.html', {
        'arriendos': arriendos,
        'ventanas': VENTANAS,
        'ventana_actual': clave_ventana,
    })


def crear_arriendo(request):
    """Asigna un equipo a un cliente.

    El formulario ya limita los equipos a los disponibles, así que aquí solo
    queda la regla que cruza modelos: un equipo no puede tener dos contratos
    vigentes. Al arrendarlo la máquina sale a faena; vuelve a estar disponible
    cuando el planificador marca su regreso, no al cerrar el contrato.
    """
    if request.method == 'POST':
        form = ArriendoForm(request.POST)
        if form.is_valid():
            equipo = form.cleaned_data['equipo']
            if Arriendo.objects.vigentes().filter(equipo=equipo).exists():
                form.add_error('equipo', 'El equipo ya tiene un arriendo vigente.')
            else:
                form.save()
                equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
                return redirect('arriendos:arriendos')
    else:
        form = ArriendoForm(initial={'equipo': request.GET.get('equipo')})
    return render(request, 'arriendos/crear.html', {'form': form})


def cerrar_arriendo(request, pk):
    """Cierra un arriendo fijando su fecha de término."""
    arriendo = get_object_or_404(Arriendo, pk=pk)
    if request.method == 'POST':
        form = CerrarArriendoForm(request.POST)
        if form.is_valid():
            arriendo.cerrar(form.cleaned_data['fecha_termino'])
            return redirect('arriendos:arriendos')
    else:
        form = CerrarArriendoForm(initial={'fecha_termino': timezone.localdate()})
    return render(request, 'arriendos/cerrar.html', {'form': form, 'arriendo': arriendo})
