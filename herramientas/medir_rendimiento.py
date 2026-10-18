"""Mide tiempo y consultas SQL de las vistas principales con una flota ampliada.

Uso (desde scr/):  python herramientas/medir_rendimiento.py [N_EQUIPOS] [N_REPETICIONES]
Crea una base de pruebas temporal, la llena con N equipos y dos años de historial
(lecturas semanales y órdenes de trabajo cerradas) y mide cada vista con el cliente de pruebas.
"""
import os
import statistics
import sys
import time
from datetime import timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vilas_motor.settings')

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.utils import timezone  # noqa: E402


def poblar(n_equipos):
    from cuentas.models import Cliente, Rol, Usuario
    from flota.models import Equipo, TipoEquipo
    from horometros.models import LecturaHorometro, SolicitudHorometro
    from mantencion.models import OrdenTrabajo, PlanMantencion, ServicioPlan
    from arriendos.models import Arriendo

    Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
    usuario = Usuario.objects.create_user(email='perf@vilas.cl', password='x', nombre='Perf')
    clientes = [Cliente.objects.create(rut=f'{i}-K', razon_social=f'Cliente {i}') for i in range(20)]
    tipos = []
    for t in range(5):
        tipo = TipoEquipo.objects.create(nombre=f'Tipo {t}', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        plan = PlanMantencion.objects.create(tipo_equipo=tipo, nombre=f'Plan {t}')
        servicios = [ServicioPlan.objects.create(plan=plan, nombre=f'{h} HORAS', intervalo_horas=h) for h in (250, 500, 1000)]
        tipos.append((tipo, servicios))
    ahora = timezone.now()
    for i in range(n_equipos):
        tipo, servicios = tipos[i % 5]
        equipo = Equipo.objects.create(tipo_equipo=tipo, codigo=f'EQ-{i:04d}', horometro_actual=Decimal('0'))
        lecturas = [
            LecturaHorometro(equipo=equipo, usuario=usuario, valor=Decimal(semana * 30),
                             fecha_hora=ahora - timedelta(weeks=104 - semana), fuente=LecturaHorometro.Fuente.CLIENTE)
            for semana in range(1, 105)
        ]
        LecturaHorometro.objects.bulk_create(lecturas)
        Equipo.objects.filter(pk=equipo.pk).update(horometro_actual=Decimal(104 * 30))
        for k, servicio in enumerate(servicios):
            for j in range(1, 8):
                OrdenTrabajo.objects.create(
                    equipo=equipo, servicio_plan=servicio, tipo=OrdenTrabajo.Tipo.PREVENTIVA,
                    estado=OrdenTrabajo.Estado.CERRADA, numero_ot=f'OT-{i:04d}{k}{j}',
                    horometro_cierre=Decimal(j * servicio.intervalo_horas // 2))
        if i % 3 == 0:
            Arriendo.objects.create(equipo=equipo, cliente=clientes[i % 20], usuario=usuario,
                                    fecha_inicio=(ahora - timedelta(days=30)).date()) if hasattr(Arriendo, 'usuario') else \
                Arriendo.objects.create(equipo=equipo, cliente=clientes[i % 20], fecha_inicio=(ahora - timedelta(days=30)).date())
        if i % 4 == 0:
            SolicitudHorometro.objects.create(equipo=equipo, usuario_solicita=usuario, fuente='CLIENTE', fecha_solicitud=ahora)
    return usuario


def medir(cliente, ruta, repeticiones):
    tiempos, consultas = [], 0
    for _ in range(repeticiones):
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            r = cliente.get(ruta)
            tiempos.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200, (ruta, r.status_code)
        consultas = len(ctx)
    return statistics.median(tiempos), max(tiempos), consultas


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    runner = DiscoverRunner(verbosity=0, interactive=False)
    runner.setup_test_environment()
    antiguo = runner.setup_databases()
    try:
        t0 = time.perf_counter()
        usuario = poblar(n)
        print(f'Datos: {n} equipos, {n * 104} lecturas, {n * 21} OT (carga {time.perf_counter() - t0:.1f} s)')
        from django.test import Client
        from flota.models import Equipo
        c = Client(); c.force_login(usuario)
        pk = Equipo.objects.first().pk
        rutas = [('Panel (dashboard)', '/dashboard/'), ('Bandeja de horómetros', '/horometros/'),
                 ('Arriendos', '/arriendos/'), ('Órdenes de trabajo', '/ordenes-trabajo/'),
                 ('Equipos', '/equipos/'), ('Ficha del equipo', f'/equipos/{pk}/')]
        print(f'{"Vista":28}{"Mediana ms":>12}{"Máx ms":>10}{"Consultas SQL":>15}')
        for nombre, ruta in rutas:
            med, mx, q = medir(c, ruta, reps)
            print(f'{nombre:28}{med:12.0f}{mx:10.0f}{q:15d}')
    finally:
        runner.teardown_databases(antiguo)
        runner.teardown_test_environment()


if __name__ == '__main__':
    main()
