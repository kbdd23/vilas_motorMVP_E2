from django.contrib import messages
from django.contrib.auth.decorators import login_not_required, user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse

from arriendos.models import Arriendo
from cuentas.forms import ClienteForm, UsuarioForm, VerificacionForm
from cuentas.models import Cliente, Usuario
from cuentas.services import codigoEsValido, confirmarCuenta, enviarCodigoVerificacion
from flota.models import Equipo
from flota.services import ESTADOS_SIN_DEVOLVER
from horometros.models import SolicitudHorometro
from mantencion.models import OrdenTrabajo
from mantencion.services import CalculadoraProximoServicio

UMBRAL_ALERTA_HORAS = 100


def _pronostico_mantencion(equipos):
    """Calcula el estado del próximo servicio para cada equipo de la flota."""
    calculadora = CalculadoraProximoServicio(umbral_alerta_horas=UMBRAL_ALERTA_HORAS)
    filas = []
    vencidos = 0
    por_vencer = 0
    pronosticos = calculadora.proximosServicios(equipos)
    for equipo in equipos:
        proximo, horas_restantes = pronosticos[equipo.id]
        if proximo is None:
            estado_alerta = 'SIN_PLAN'
        elif horas_restantes < 0:
            estado_alerta = 'VENCIDO'
            vencidos += 1
        elif horas_restantes <= UMBRAL_ALERTA_HORAS:
            estado_alerta = 'POR_VENCER'
            por_vencer += 1
        else:
            estado_alerta = 'AL_DIA'
        filas.append({
            'equipo': equipo,
            'proximo': proximo,
            'horas_restantes': horas_restantes,
            'estado_alerta': estado_alerta,
        })
    return filas, vencidos, por_vencer



def home(request):
    """El panel es uno solo: la entrada de inicio lleva al dashboard."""
    return redirect('cuentas:dashboard')


def catalogos(request):
    """Índice de catálogos: acceso a cada listado maestro."""
    return render(request, 'cuentas/catalogos.html')


def lista_clientes(request):
    """Cartera de clientes."""
    clientes = Cliente.objects.order_by('razon_social')
    return render(request, 'cuentas/clientes.html', {'clientes': clientes})


def crear_cliente(request):
    """Crea un cliente en la cartera."""
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cuentas:clientes')
    else:
        form = ClienteForm()
    return render(request, 'cuentas/crear_cliente.html', {'form': form})



@user_passes_test(lambda usuario: usuario.is_staff)
def lista_usuarios(request):
    """Directorio de acceso. Solo el personal autorizado puede administrarlo."""
    usuarios = Usuario.objects.select_related('rol', 'cliente').order_by('nombre', 'email')
    return render(request, 'cuentas/usuarios.html', {'usuarios': usuarios})


@user_passes_test(lambda usuario: usuario.is_staff)
def crear_usuario(request):
    """Crea una cuenta que inicia sesión con su dirección de correo.

    Reemplaza el registro abierto: solo el personal autorizado da acceso al
    sistema. La cuenta nace sin verificar y confirma su correo en el primer ingreso.
    """
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            # El alta desde la interfaz nunca entrega privilegios de superusuario.
            usuario.is_staff = True
            usuario.is_superuser = False
            usuario.save()
            messages.success(request, f'Usuario {usuario.email} creado correctamente.')
            return redirect('cuentas:usuarios')
    else:
        form = UsuarioForm()
    return render(request, 'cuentas/crear_usuario.html', {'form': form})


@login_not_required
def diagnostico(request):
    """Informa qué backend de correo está activo en este deployment.

    Solo devuelve booleanos y nombres de configuración: ninguna credencial.
    Existe para comprobar el entorno de producción y se retira después.
    """
    from django.conf import settings
    from django.http import JsonResponse

    return JsonResponse({
        'backend': settings.EMAIL_BACKEND,
        'brevo_key_configurada': bool(settings.BREVO_API_KEY),
        'brevo_remitente': settings.BREVO_REMITENTE,
        'gmail_usuario_configurado': bool(settings.EMAIL_HOST_USER),
        'remitente_por_defecto': settings.DEFAULT_FROM_EMAIL,
    })



def verificar(request):
    """Confirma la cuenta con el código que llegó al correo."""
    if request.user.email_verificado:
        return redirect('cuentas:dashboard')

    if request.method == 'POST':
        form = VerificacionForm(request.POST)
        if form.is_valid():
            if codigoEsValido(request.user, form.cleaned_data['codigo']):
                confirmarCuenta(request.user)
                return redirect('cuentas:dashboard')
            form.add_error('codigo', 'El código no es correcto o ya venció.')
    else:
        form = VerificacionForm()

    return render(request, 'cuentas/verificar.html', {
        'form': form,
        'reenviado': request.GET.get('enviado') == '1',
    })


def reenviar_codigo(request):
    """Manda un código nuevo a la cuenta que todavía no se confirma."""
    if request.method == 'POST' and not request.user.email_verificado:
        enviarCodigoVerificacion(request.user)
    return redirect(f"{reverse('cuentas:verificar')}?enviado=1")


def dashboard(request):
    """Panel operativo: lo que hay que hacer y cómo está la flota.

    El corazón no son los contadores sino las colas de trabajo que salen de las
    bandejas: pedir los horómetros que faltan, atender la mantención que venció o
    está por vencer, ejecutar las órdenes abiertas y recuperar los equipos que no
    volvieron. Abajo, el pronóstico por equipo da el detalle de cuál máquina
    necesita qué.
    """
    equipos = list(Equipo.objects.select_related('tipo_equipo').order_by('codigo'))
    conteo_estados = {estado: 0 for estado, _ in Equipo.Estado.choices}
    for equipo in equipos:
        conteo_estados[equipo.estado] += 1
    filas, vencidos, por_vencer = _pronostico_mantencion(equipos)

    # Equipos que cerraron su arriendo pero siguen sin volver a bodega: su último
    # contrato terminó y la máquina sigue en faena. Un equipo interno o en taller no
    # cuenta: no está pendiente el regreso de un arriendo.
    equipos_sin_devolver = 0
    en_faena = Equipo.objects.filter(estado__in=ESTADOS_SIN_DEVOLVER).prefetch_related('arriendos')
    for equipo in en_faena:
        ultimo = max(equipo.arriendos.all(), key=lambda a: (a.fecha_inicio, a.id), default=None)
        if ultimo is not None and ultimo.fecha_termino is not None:
            equipos_sin_devolver += 1

    total_equipos = len(equipos)

    def datos_grafico(elementos, total):
        """Prepara valores y porcentajes para gráficos de barras accesibles."""
        return [
            {
                **elemento,
                'porcentaje': round((elemento['cantidad'] / total) * 100, 1) if total else 0,
            }
            for elemento in elementos
        ]

    estados_flotas = datos_grafico([
        {'nombre': 'Disponible', 'cantidad': conteo_estados[Equipo.Estado.DISPONIBLE], 'tono': 'verde'},
        {'nombre': 'En faena', 'cantidad': conteo_estados[Equipo.Estado.EN_FAENA], 'tono': 'azul'},
        {'nombre': 'En mantenimiento', 'cantidad': conteo_estados[Equipo.Estado.EN_MANTENIMIENTO], 'tono': 'naranja'},
        {'nombre': 'Interno', 'cantidad': conteo_estados[Equipo.Estado.INTERNO], 'tono': 'gris'},
    ], total_equipos)
    salud_mantencion = datos_grafico([
        {'nombre': 'Vencida', 'cantidad': vencidos, 'tono': 'rojo'},
        {'nombre': 'Próxima', 'cantidad': por_vencer, 'tono': 'naranja'},
        {'nombre': 'Al día', 'cantidad': sum(1 for fila in filas if fila['estado_alerta'] == 'AL_DIA'), 'tono': 'verde'},
        {'nombre': 'Sin plan', 'cantidad': sum(1 for fila in filas if fila['estado_alerta'] == 'SIN_PLAN'), 'tono': 'gris'},
    ], total_equipos)
    colores_donut = {'verde': '#19a463', 'azul': '#378fe5', 'naranja': '#f5a52b', 'gris': '#a6b2bd'}
    punto = 0
    segmentos_donut = []
    for item in estados_flotas:
        siguiente = punto + item['porcentaje']
        if item['cantidad']:
            segmentos_donut.append(f"{colores_donut[item['tono']]} {punto}% {siguiente}%")
        punto = siguiente

    total_ot = OrdenTrabajo.objects.count()
    ordenes_por_estado = datos_grafico([
        {'nombre': 'Abiertas', 'cantidad': OrdenTrabajo.objects.filter(estado=OrdenTrabajo.Estado.PROGRAMADA).count(), 'tono': 'azul'},
        {'nombre': 'En proceso', 'cantidad': OrdenTrabajo.objects.filter(estado=OrdenTrabajo.Estado.EN_CURSO).count(), 'tono': 'naranja'},
        {'nombre': 'Cerradas', 'cantidad': OrdenTrabajo.objects.filter(estado=OrdenTrabajo.Estado.CERRADA).count(), 'tono': 'gris'},
    ], total_ot)

    return render(request, 'cuentas/dashboard.html', {
        'total_equipos': total_equipos,
        'equipos_disponibles': conteo_estados[Equipo.Estado.DISPONIBLE],
        'porcentaje_disponibles': round(
            (conteo_estados[Equipo.Estado.DISPONIBLE] / total_equipos) * 100, 1
        ) if total_equipos else 0,
        'total_clientes': Cliente.objects.count(),
        'total_arriendos': Arriendo.objects.count(),
        'total_ot': total_ot,
        'solicitudes_pendientes': SolicitudHorometro.objects.filter(
            estado=SolicitudHorometro.Estado.PENDIENTE
        ).count(),
        'servicios_vencidos': vencidos,
        'servicios_por_vencer': por_vencer,
        'ots_abiertas': OrdenTrabajo.objects.exclude(
            estado=OrdenTrabajo.Estado.CERRADA
        ).count(),
        'equipos_sin_devolver': equipos_sin_devolver,
        'umbral_alerta': UMBRAL_ALERTA_HORAS,
        'estados_flotas': estados_flotas,
        'salud_mantencion': salud_mantencion,
        'flota_donut': ', '.join(segmentos_donut) or '#e9eeeb 0 100%',
        'ordenes_por_estado': ordenes_por_estado,
        'is_dashboard': True,
    })


def _render_bandeja_mantencion(request, estados_alerta, titulo, descripcion, mensaje_vacio):
    """Renderiza una bandeja de mantención para los estados indicados."""
    equipos = list(Equipo.objects.select_related('tipo_equipo').order_by('codigo'))
    filas, vencidos, por_vencer = _pronostico_mantencion(equipos)
    filas_bandeja = [
        fila for fila in filas
        if fila['estado_alerta'] in estados_alerta
    ]
    return render(request, 'cuentas/mantenimientos_pendientes.html', {
        'titulo': titulo,
        'descripcion': descripcion,
        'mensaje_vacio': mensaje_vacio,
        'filas': filas_bandeja,
        'servicios_vencidos': vencidos,
        'servicios_por_vencer': por_vencer,
        'umbral_alerta': UMBRAL_ALERTA_HORAS,
    })


def mantenimientos_pendientes(request):
    """Bandeja de equipos con servicio vencido o próximo a vencer."""
    return _render_bandeja_mantencion(
        request,
        {'VENCIDO', 'POR_VENCER'},
        'Mantenciones por atender',
        f'Equipos con servicio vencido o dentro de las próximas {UMBRAL_ALERTA_HORAS} horas.',
        'No hay mantenciones por atender. La flota está al día.',
    )


def mantenimientos_vencidos(request):
    """Bandeja prioritaria de servicios que ya superaron su intervalo."""
    return _render_bandeja_mantencion(
        request,
        {'VENCIDO'},
        'Mantenciones vencidas',
        'Servicios cuyo intervalo ya fue cumplido y deben priorizarse.',
        'No hay mantenciones vencidas.',
    )


def mantenimientos_por_vencer(request):
    """Bandeja preventiva de servicios dentro del umbral de alerta."""
    return _render_bandeja_mantencion(
        request,
        {'POR_VENCER'},
        'Mantenciones por vencer',
        f'Servicios que se deben programar dentro de las próximas {UMBRAL_ALERTA_HORAS} horas.',
        'No hay mantenciones próximas dentro del umbral.',
    )
