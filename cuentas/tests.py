from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arriendos.models import Arriendo
from cuentas.models import Cliente, Rol, Usuario
from flota.models import Equipo, TipoEquipo
from horometros.models import SolicitudHorometro
from mantencion.models import OrdenTrabajo, PlanMantencion, ServicioPlan


class DashboardTest(TestCase):
    """El panel operativo: cuenta el trabajo pendiente y distingue vencido de por vencer."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(
            nombre='planificador',
            defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'},
        )
        self.usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-001', horometro_actual=Decimal('150.0')
        )
        self.client.force_login(self.usuario)

    def test_home_redirige_al_dashboard(self):
        self.assertRedirects(self.client.get('/'), reverse('cuentas:dashboard'))

    def test_cuenta_lo_que_hay_que_hacer(self):
        """Los contadores salen de las bandejas, no de la imaginación."""
        SolicitudHorometro.objects.create(
            equipo=self.equipo, cliente=self.cliente, usuario_solicita=self.usuario,
            fuente='CLIENTE', fecha_solicitud=timezone.now(),
        )
        OrdenTrabajo.objects.create(
            equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-001'
        )
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan')
        ServicioPlan.objects.create(plan=plan, nombre='100h', intervalo_horas=100)

        contexto = self.client.get(reverse('cuentas:dashboard')).context
        self.assertEqual(contexto['solicitudes_pendientes'], 1)
        self.assertEqual(contexto['servicios_vencidos'], 1)  # 150h contra intervalo de 100
        self.assertEqual(contexto['servicios_por_vencer'], 0)
        self.assertEqual(contexto['ots_abiertas'], 1)

    def test_separa_vencido_de_por_vencer(self):
        """Un servicio sobre el intervalo es vencido; dentro del umbral, por vencer."""
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan')
        ServicioPlan.objects.create(plan=plan, nombre='100h', intervalo_horas=100)
        Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-002', horometro_actual=Decimal('50.0')
        )

        html = self.client.get(reverse('cuentas:dashboard')).content.decode()
        self.assertEqual(html.count('>Vencido<'), 1)
        self.assertEqual(html.count('>Por vencer<'), 1)

    def test_cuenta_el_equipo_que_no_volvio(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=date(2026, 1, 5)
        )
        arriendo.cerrar(date(2026, 6, 30))

        contexto = self.client.get(reverse('cuentas:dashboard')).context
        self.assertEqual(contexto['equipos_sin_devolver'], 1)

    def test_las_colas_enlazan_donde_se_resuelven(self):
        response = self.client.get(reverse('cuentas:dashboard'))
        self.assertContains(response, reverse('horometros:index'))
        self.assertContains(response, reverse('mantencion:ordenes_trabajo'))
        self.assertContains(response, reverse('arriendos:arriendos'))
        self.assertContains(response, 'href="#pronostico"')

    def test_el_pronostico_ofrece_crear_la_ot(self):
        """Un vencido no es un callejón sin salida: hay un botón que abre el alta."""
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan')
        servicio = ServicioPlan.objects.create(plan=plan, nombre='100h', intervalo_horas=100)

        response = self.client.get(reverse('cuentas:dashboard'))
        self.assertContains(response, '>Crear OT<')
        self.assertContains(
            response,
            reverse('mantencion:crear_orden') + f'?equipo={self.equipo.id}&servicio={servicio.id}',
        )


class UsuarioManagerTest(TestCase):
    """Anti-escalada de privilegios: las cuentas no pueden elegir su rol ni sus permisos."""

    def setUp(self):
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})

    def test_create_user_rechaza_rol_y_permisos(self):
        for campo in ('rol', 'is_staff', 'is_superuser'):
            with self.assertRaises(ValueError):
                Usuario.objects.create_user(email='a@v.cl', password='x', nombre='A', **{campo: True})

    def test_create_user_asigna_rol_planificador_sin_superusuario(self):
        u = Usuario.objects.create_user(email='b@v.cl', password='x', nombre='B')
        self.assertEqual(u.rol.nombre, 'planificador')
        self.assertTrue(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertNotEqual(u.password, 'x')  # se guarda el hash, no la contraseña

    def test_create_superuser(self):
        u = Usuario.objects.create_superuser(email='c@v.cl', password='x', nombre='C')
        self.assertTrue(u.is_superuser and u.is_staff and u.is_active)

    def test_email_obligatorio(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email='', password='x', nombre='D')

    def test_rol_inexistente(self):
        Rol.objects.all().delete()
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(email='e@v.cl', password='x', nombre='E')


class SinDevolverPorEstadoTest(TestCase):
    """Solo un equipo en faena con el arriendo cerrado cuenta como sin devolver."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.client.force_login(self.usuario)

    def _con_arriendo_cerrado(self, estado):
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo=f'EQ-{estado}', estado=estado)
        arriendo = Arriendo.objects.create(equipo=equipo, cliente=self.cliente, fecha_inicio=date(2026, 1, 5))
        arriendo.cerrar(date(2026, 6, 30))
        return equipo

    def test_un_equipo_interno_no_cuenta_como_sin_devolver(self):
        self._con_arriendo_cerrado(Equipo.Estado.INTERNO)
        contexto = self.client.get(reverse('cuentas:dashboard')).context
        self.assertEqual(contexto['equipos_sin_devolver'], 0)

    def test_un_equipo_en_faena_si_cuenta(self):
        self._con_arriendo_cerrado(Equipo.Estado.EN_FAENA)
        contexto = self.client.get(reverse('cuentas:dashboard')).context
        self.assertEqual(contexto['equipos_sin_devolver'], 1)
