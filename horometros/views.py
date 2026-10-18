from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from flota.models import Equipo
from vilas_motor.ventanas import VENTANA_POR_DEFECTO, VENTANAS, dias_de_ventana

from .forms import LecturaDeSolicitudForm, SolicitudHorometroForm
from .models import LecturaHorometro, SolicitudHorometro
from .services import ValidadorDatos, arrendatarioDelEquipo

# Mensaje único para el caso de un equipo sin arrendatario: lo usan el error del
# formulario y la respuesta que llena la celda del cliente, para que digan lo mismo.
SIN_ARRENDATARIO = 'Este equipo no tiene un cliente con arriendo asociado.'


LIMITE_LECTURAS = 100


def _render_pagina(request, form_lectura=None, solicitud_en_edicion=None,
                   form_solicitud=None, abrir_solicitud=False):
    """Arma la página de horómetros: las dos celdas y sus dos diálogos.

    Los diálogos se abren solos cuando el servidor reenvía la página después de un
    POST que no pasó la validación, así el error queda a la vista y no se pierde lo
    que se había escrito. En el caso normal los abre el navegador, sin pedirle nada
    al servidor.
    """
    clave_ventana = request.GET.get('ventana', VENTANA_POR_DEFECTO)
    # La ventana acá es un rango móvil sobre la fecha de resolución, que es un
    # instante y no un día: así "24 horas" son 24 horas de verdad. La bandeja de
    # arriendos no puede hacer lo mismo porque su fecha de término es un día
    # calendario, y ahí la ventana se cuenta en días.
    limite = timezone.now() - timedelta(days=dias_de_ventana(clave_ventana))

    solicitudes = (
        SolicitudHorometro.objects.select_related('equipo', 'cliente', 'lectura')
        .filter(
            Q(estado=SolicitudHorometro.Estado.PENDIENTE)
            | Q(fecha_resolucion__gte=limite)
        )
        .order_by('-fecha_solicitud', '-id')
    )
    # El historial puede crecer sin límite: se muestran las últimas lecturas, no todas.
    lecturas = LecturaHorometro.objects.select_related('equipo').order_by('-fecha_hora')[:LIMITE_LECTURAS]

    if form_lectura is None:
        form_lectura = LecturaDeSolicitudForm()
    if form_solicitud is None:
        form_solicitud = SolicitudHorometroForm(initial={
            'fuente': request.GET.get('fuente'),
            'equipo': request.GET.get('equipo'),
        })

    return render(request, 'horometros/index.html', {
        'solicitudes': solicitudes,
        'lecturas': lecturas,
        'ventanas': VENTANAS,
        'ventana_actual': clave_ventana,
        'form_lectura': form_lectura,
        'solicitud_en_edicion': solicitud_en_edicion,
        'form_solicitud': form_solicitud,
        'abrir_solicitud': abrir_solicitud or bool(request.GET.get('nueva')),
    })


def index(request):
    """Página de horómetros: la bandeja de trabajo y el historial de lecturas.

    La bandeja lista toda solicitud que tenga un paso pendiente: una solicitud se
    resuelve en un paso, ingresar el dato que se recibió, y mientras no llegue
    sigue ahí sin importar cuánto tiempo pase. La ventana gobierna solo las ya
    resueltas, para que la resolución del día se alcance a ver antes de
    desaparecer. El historial es el archivo, y vive plegado abajo.

    No se deduplica por equipo, a diferencia de la bandeja de arriendos: dos
    solicitudes pendientes de la misma máquina son dos obligaciones distintas y el
    planificador necesita verlas para contrastar el dato real.
    """
    return _render_pagina(request)


@login_required
def crear_solicitud(request):
    """Crea una solicitud de horómetro hacia la fuente elegida.

    El cliente no se pide en el formulario: se deriva del equipo, que es quien lo
    tiene. Así no se puede mandar un cliente ajeno ni inventado.

    No tiene página propia: el formulario vive en un diálogo de la bandeja. El GET
    abre el diálogo sobre la página, y un POST que no pasa la validación la devuelve
    con el diálogo abierto y el error a la vista.
    """
    if request.method == 'POST':
        form = SolicitudHorometroForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            if solicitud.esDelCliente():
                solicitud.cliente = arrendatarioDelEquipo(solicitud.equipo)
                if solicitud.cliente is None:
                    form.add_error('equipo', SIN_ARRENDATARIO)
                    return _render_pagina(request, form_solicitud=form, abrir_solicitud=True)
            solicitud.usuario_solicita = request.user
            solicitud.fecha_solicitud = timezone.now()
            solicitud.save()
            return redirect('horometros:index')
        return _render_pagina(request, form_solicitud=form, abrir_solicitud=True)

    return _render_pagina(request, abrir_solicitud=True)


def _respeta_el_horometro(form, equipo):
    """True si el valor del formulario cumple la regla del horómetro.

    Si no la cumple deja el error en el campo 'valor' con un mensaje entendible,
    en vez del genérico de Django.
    """
    if ValidadorDatos().validar(equipo, form.cleaned_data['valor']):
        return True
    form.add_error('valor', 'La lectura no puede ser menor al horómetro actual del equipo.')
    return False


@login_required
def registrar_lectura(request, pk):
    """Cierra una solicitud con el horómetro que se recibió.

    No tiene página propia: la bandeja lo resuelve en un diálogo. Un solo acto
    cierra el paso, creando la lectura, vinculándola a la solicitud y actualizando
    el horómetro del equipo. La lectura hereda la fuente de la solicitud y nace
    validada, porque la tipea el planificador, que es quien confirma.

    Se entra por acá cuando el POST falla la validación, o por la URL directa.
    """
    solicitud = get_object_or_404(
        SolicitudHorometro.objects.select_related('equipo', 'cliente'), pk=pk
    )
    if not solicitud.estaPendiente():
        return redirect('horometros:index')

    if request.method == 'POST':
        form = LecturaDeSolicitudForm(request.POST)
        if form.is_valid() and _respeta_el_horometro(form, solicitud.equipo):
            lectura = form.save(commit=False)
            lectura.equipo = solicitud.equipo
            lectura.fuente = solicitud.fuente
            lectura.usuario = request.user
            lectura.fecha_hora = timezone.now()
            lectura.validada = True
            lectura.save()
            solicitud.cumplir(lectura)
            solicitud.equipo.actualizarHorometro(lectura.valor)
            return redirect('horometros:index')
        return _render_pagina(request, form_lectura=form, solicitud_en_edicion=solicitud)

    return _render_pagina(request, solicitud_en_edicion=solicitud)


@login_required
@require_POST
def borrar_solicitud(request, pk):
    """Borra una solicitud pendiente.

    Es la salida para el error del planificador: si pidió un horómetro que no
    correspondía, la borra en vez de arrastrarla pendiente para siempre. No toca
    lecturas, porque una solicitud pendiente no tiene ninguna vinculada.
    """
    solicitud = get_object_or_404(SolicitudHorometro, pk=pk)
    if solicitud.estaPendiente():
        solicitud.delete()
    return redirect('horometros:index')


@login_required
def arrendatario_del_equipo(request, pk):
    """Arrendatario de un equipo, para llenar la celda del cliente.

    Es solo informativo: el cliente de la solicitud lo deriva el servidor al
    guardarla, así que esto no reemplaza ninguna validación.
    """
    equipo = get_object_or_404(Equipo, pk=pk)
    cliente = arrendatarioDelEquipo(equipo)
    if cliente is None:
        return JsonResponse({'cliente': None, 'mensaje': SIN_ARRENDATARIO})
    return JsonResponse({'cliente': cliente.razon_social})
