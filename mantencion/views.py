from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from flota.models import Equipo
from flota.services import mensajeDeBloqueo, puedeEntrarAMantencion

from .forms import (
    CerrarOrdenForm,
    OrdenTrabajoForm,
    OrdenTrabajoInsumoForm,
    PlanMantencionForm,
    ServicioPlanForm,
)
from .models import OrdenTrabajo, PlanMantencion, ServicioPlan
from .services import registrarCierreDeOrden


def lista_planes(request):
    """Planes de mantención y sus servicios por tipo de equipo."""
    planes = PlanMantencion.objects.select_related('tipo_equipo').annotate(
        total_servicios=Count('servicios')
    ).order_by('nombre')
    servicios = ServicioPlan.objects.select_related('plan__tipo_equipo').annotate(
        total_ots=Count('ordenes_trabajo')
    ).order_by('intervalo_horas')
    return render(request, 'mantencion/planes.html', {'planes': planes, 'servicios': servicios})


def _render_lista(request, form_orden=None, abrir_orden=False):
    """Arma la lista de OTs, con el diálogo de alta listo para usar.

    El alta vive en un diálogo de la misma lista, así que el formulario se arma acá.
    El diálogo se abre solo cuando el POST no pasó la validación, para que el error
    quede a la vista; en el caso normal lo abre el navegador.
    """
    ordenes = OrdenTrabajo.objects.select_related('equipo', 'servicio_plan').order_by('-id')
    if form_orden is None:
        initial = {'equipo': request.GET.get('equipo')}
        if request.GET.get('servicio'):
            initial['servicio_plan'] = request.GET.get('servicio')
        form_orden = OrdenTrabajoForm(initial=initial)
    return render(request, 'mantencion/ordenes_trabajo.html', {
        'ordenes': ordenes,
        'form_orden': form_orden,
        'abrir_orden': abrir_orden,
    })


def lista_ordenes_trabajo(request):
    """Órdenes de trabajo programadas y ejecutadas."""
    return _render_lista(request)


def crear_plan(request):
    """Crea un plan de mantención para un tipo de equipo."""
    if request.method == 'POST':
        form = PlanMantencionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('mantencion:planes')
    else:
        form = PlanMantencionForm()
    return render(request, 'mantencion/crear_plan.html', {'form': form})


def editar_plan(request, pk):
    """Edita un plan de mantención (nombre y tipo de equipo)."""
    plan = get_object_or_404(PlanMantencion, pk=pk)
    if request.method == 'POST':
        form = PlanMantencionForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            return redirect('mantencion:planes')
    else:
        form = PlanMantencionForm(instance=plan)
    return render(request, 'mantencion/editar_plan.html', {'form': form, 'plan': plan})


@require_POST
def borrar_plan(request, pk):
    """Borra un plan que no tiene servicios.

    Un plan con servicios no se puede borrar: el servicio depende de él (FK con
    PROTECT), así que primero hay que quitar sus servicios.
    """
    plan = get_object_or_404(PlanMantencion, pk=pk)
    if plan.servicios.count() == 0:
        plan.delete()
    return redirect('mantencion:planes')


def crear_servicio(request):
    """Crea un servicio (con su intervalo) dentro de un plan."""
    if request.method == 'POST':
        form = ServicioPlanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('mantencion:planes')
    else:
        form = ServicioPlanForm()
    return render(request, 'mantencion/crear_servicio.html', {'form': form})


def editar_servicio(request, pk):
    """Edita un servicio (nombre, intervalo y descripción).

    Cambiar el intervalo redefine el plan hacia adelante: el historial de OTs no
    se toca, solo se recalcula cuánto falta para la próxima mantención.
    """
    servicio = get_object_or_404(ServicioPlan, pk=pk)
    if request.method == 'POST':
        form = ServicioPlanForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return redirect('mantencion:planes')
    else:
        form = ServicioPlanForm(instance=servicio)
    return render(request, 'mantencion/editar_servicio.html', {'form': form, 'servicio': servicio})


@require_POST
def borrar_servicio(request, pk):
    """Borra un servicio que no está usado en ninguna OT.

    Un servicio con OTs es parte del historial: borrarlo dejaría huérfana la OT
    (FK con PROTECT), así que no se toca.
    """
    servicio = get_object_or_404(ServicioPlan, pk=pk)
    if servicio.ordenes_trabajo.count() == 0:
        servicio.delete()
    return redirect('mantencion:planes')


def crear_orden(request):
    """Programa una nueva OT desde el diálogo de la lista.

    El número se genera automáticamente (OT-0001...). No tiene página propia: el
    GET abre el diálogo sobre la lista, y un POST que no pasa la validación la
    devuelve con el diálogo abierto y el error a la vista.
    """
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.numero_ot = 'TEMP'
            orden.save()
            orden.numero_ot = f'OT-{orden.id:04d}'
            orden.save(update_fields=['numero_ot'])
            return redirect('mantencion:detalle_orden', pk=orden.pk)
        return _render_lista(request, form_orden=form, abrir_orden=True)

    return _render_lista(request, abrir_orden=True)


def editar_orden(request, pk):
    """Edita una OT que aún no se cierra.

    Una OT CERRADA es historial de mantención: su horómetro de cierre alimenta la
    calculadora del próximo servicio, así que editarla cambiaría el pronóstico
    hacia atrás. Lo que se puede corregir se corrige antes de cerrar.
    """
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if orden.estado == OrdenTrabajo.Estado.CERRADA:
        return redirect('mantencion:detalle_orden', pk=orden.pk)

    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST, instance=orden)
        if form.is_valid():
            form.save()
            return redirect('mantencion:detalle_orden', pk=orden.pk)
    else:
        form = OrdenTrabajoForm(instance=orden)
    return render(request, 'mantencion/editar_orden.html', {'form': form, 'orden': orden})


def _render_detalle(request, orden, form_cierre=None, abrir_cierre=False):
    """Arma la ficha de la OT con su diálogo de cierre listo para usar.

    El cierre vive en un diálogo de la ficha, así que el formulario se arma acá.
    El diálogo se abre solo cuando el POST no pasó la validación, para que el error
    quede a la vista; en el caso normal lo abre el navegador, o el enlace de la
    lista que llega con ?cerrar=1.
    """
    if form_cierre is None:
        form_cierre = CerrarOrdenForm(equipo=orden.equipo)
    return render(request, 'mantencion/detalle_orden.html', {
        'orden': orden,
        'form_cierre': form_cierre,
        'abrir_cierre': abrir_cierre or bool(request.GET.get('cerrar')),
    })


def detalle_orden(request, pk):
    """Ficha de una OT con sus insumos usados."""
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related('equipo', 'servicio_plan').prefetch_related('insumos__insumo'),
        pk=pk,
    )
    return _render_detalle(request, orden)


def registrar_insumo(request, pk):
    """Registra un insumo real usado en la OT."""
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if request.method == 'POST':
        form = OrdenTrabajoInsumoForm(request.POST)
        if form.is_valid():
            orden.registrarInsumo(
                insumo=form.cleaned_data['insumo'],
                cantidad=form.cleaned_data['cantidad_usada'],
                notas=form.cleaned_data['notas'],
            )
            return redirect('mantencion:detalle_orden', pk=orden.pk)
    else:
        form = OrdenTrabajoInsumoForm()
    return render(request, 'mantencion/registrar_insumo.html', {'form': form, 'orden': orden})


@require_POST
def iniciar_orden(request, pk):
    """Pasa una OT de PROGRAMADA a EN_CURSO y manda el equipo al taller.

    Iniciar no es solo cambiar el estado de la orden: la máquina entra a
    mantenimiento y de ahí no sale hasta que la OT se cierre. Solo puede empezar un
    equipo en bodega o en uso interno; uno en faena está con el cliente, y uno ya
    en mantenimiento tiene su OT en curso. Cuando no se puede, el aviso sale como
    toast en la lista.
    """
    orden = get_object_or_404(OrdenTrabajo.objects.select_related('equipo'), pk=pk)
    if orden.estado == OrdenTrabajo.Estado.PROGRAMADA:
        if puedeEntrarAMantencion(orden.equipo):
            orden.iniciar()
            orden.equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        else:
            messages.error(request, mensajeDeBloqueo(orden.equipo))
    return redirect('mantencion:ordenes_trabajo')


def cerrar_orden(request, pk):
    """Cierra una OT en curso fijando el horómetro de cierre.

    Solo se cierra lo que ya arrancó: una PROGRAMADA primero se pasa a EN_CURSO.
    No tiene página propia: el formulario vive en un diálogo de la ficha y postea
    acá. El cierre deja la lectura del técnico en el historial del equipo, mueve su
    horómetro y lo devuelve al estado del que vino: un equipo interno sigue siendo
    interno después del taller.
    """
    orden = get_object_or_404(OrdenTrabajo.objects.select_related('equipo'), pk=pk)
    if orden.estado != OrdenTrabajo.Estado.EN_CURSO:
        return redirect('mantencion:detalle_orden', pk=orden.pk)

    if request.method == 'POST':
        form = CerrarOrdenForm(request.POST, equipo=orden.equipo)
        if form.is_valid():
            registrarCierreDeOrden(orden, form.cleaned_data['horometro_cierre'], request.user)
            orden.equipo.volverDeMantenimiento()
            return redirect('mantencion:detalle_orden', pk=orden.pk)
        return _render_detalle(request, orden, form_cierre=form, abrir_cierre=True)

    return redirect('mantencion:detalle_orden', pk=orden.pk)


@require_POST
def borrar_orden(request, pk):
    """Borra una OT que aún no se cierra.

    Es la salida para un error de programación: se creó una OT que no correspondía
    y se quita del registro. Una CERRADA no se toca, es el historial del equipo.
    """
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if orden.estado != OrdenTrabajo.Estado.CERRADA:
        orden.delete()
    return redirect('mantencion:ordenes_trabajo')
