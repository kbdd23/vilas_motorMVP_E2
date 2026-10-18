from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arriendos.models import Arriendo
from cuentas.models import Cliente, Rol, Usuario
from flota.models import Equipo, TipoEquipo
from horometros.models import LecturaHorometro


class EquipoTest(TestCase):
    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')

    def test_cambiar_estado(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.EN_FAENA)

    def test_cambiar_estado_invalido(self):
        with self.assertRaises(ValueError):
            self.equipo.cambiarEstado('ROTO')

    def test_actualizar_horometro(self):
        self.equipo.actualizarHorometro(Decimal('250.0'))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.horometro_actual, Decimal('250.0'))

    def test_ultima_lectura(self):
        rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        LecturaHorometro.objects.create(
            equipo=self.equipo, usuario=usuario, valor=Decimal('100.0'),
            fecha_hora=timezone.now(), fuente=LecturaHorometro.Fuente.CLIENTE,
        )
        LecturaHorometro.objects.create(
            equipo=self.equipo, usuario=usuario, valor=Decimal('150.0'),
            fecha_hora=timezone.now(), fuente=LecturaHorometro.Fuente.CLIENTE,
        )
        self.assertEqual(self.equipo.ultimaLectura().valor, Decimal('150.0'))


class MarcarDisponibleTest(TestCase):
    """La vista solo devuelve el equipo a disponible cuando su arriendo terminó."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.client.force_login(self.usuario)

    def test_marcar_disponible(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        response = self.client.post(reverse('flota:marcar_disponible', args=[self.equipo.id]))
        self.assertRedirects(response, reverse('arriendos:arriendos'))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.DISPONIBLE)

    def test_no_cambia_si_el_arriendo_sigue_vigente(self):
        Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        self.client.post(reverse('flota:marcar_disponible', args=[self.equipo.id]))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.EN_FAENA)


class FlotaViewsTest(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.client.force_login(self.usuario)

    def test_detalle_equipo(self):
        response = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EQ-001')
        self.assertContains(response, 'Crear OT')
        self.assertContains(response, 'Crear arriendo')

    def test_detalle_enlaza_con_la_fuente_que_corresponde_al_estado(self):
        """El enlace llega con la fuente ya elegida: el estado dice a quién pedirle."""
        response = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.id]))
        self.assertContains(response, 'Solicitar horómetro')
        self.assertContains(response, '?fuente=TECNICO')

        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        response = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.id]))
        self.assertContains(response, '?fuente=CLIENTE')

        self.equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        response = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.id]))
        self.assertContains(response, '?fuente=TELEMETRIA')

    def test_detalle_no_ofrece_arrendar_un_equipo_que_no_esta_disponible(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        response = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.id]))
        self.assertNotContains(response, 'Crear arriendo')

    def test_preseleccion_equipo_en_crear_solicitud(self):
        response = self.client.get(
            reverse('horometros:crear_solicitud'),
            {'fuente': 'TECNICO', 'equipo': self.equipo.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{self.equipo.id}" selected')

    def test_crear_tipo_equipo(self):
        response = self.client.post(reverse('flota:crear_tipo_equipo'), {
            'nombre': 'Excavadora',
            'unidad_medida': TipoEquipo.UnidadMedida.HORAS,
        })
        self.assertRedirects(response, reverse('flota:tipos_equipo'))
        self.assertTrue(TipoEquipo.objects.filter(nombre='Excavadora').exists())

    def test_crear_equipo(self):
        response = self.client.post(reverse('flota:crear_equipo'), {
            'codigo': 'EQ-002',
            'tipo_equipo': self.tipo.id,
            'patente': '',
            'marca': '',
            'modelo': '',
            'numero_serie': '',
            'estado': Equipo.Estado.DISPONIBLE,
            'horometro_actual': '0.0',
        })
        self.assertRedirects(response, reverse('flota:equipos'))
        self.assertTrue(Equipo.objects.filter(codigo='EQ-002').exists())


class EstadoDeMantencionTest(TestCase):
    """Entrar al taller recuerda de dónde se venía; salir devuelve ahí."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)

    def _equipo(self, estado):
        return Equipo.objects.create(tipo_equipo=self.tipo, codigo=f'EQ-{estado}', estado=estado)

    def test_entrar_recuerda_el_origen(self):
        equipo = self._equipo(Equipo.Estado.INTERNO)
        equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado_previo, Equipo.Estado.INTERNO)

    def test_volver_devuelve_el_origen(self):
        equipo = self._equipo(Equipo.Estado.INTERNO)
        equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        equipo.volverDeMantenimiento()
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado, Equipo.Estado.INTERNO)
        self.assertIsNone(equipo.estado_previo)

    def test_volver_sin_origen_deja_disponible(self):
        equipo = self._equipo(Equipo.Estado.DISPONIBLE)
        equipo.volverDeMantenimiento()
        equipo.refresh_from_db()
        self.assertEqual(equipo.estado, Equipo.Estado.DISPONIBLE)

    def test_cambiar_a_otro_estado_limpia_el_origen(self):
        equipo = self._equipo(Equipo.Estado.INTERNO)
        equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        equipo.refresh_from_db()
        self.assertIsNone(equipo.estado_previo)


class CapacidadesTest(TestCase):
    """La tabla de capacidades es la única que decide qué se puede hacer con cada estado."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)

    def test_la_tabla_cubre_todos_los_estados(self):
        from flota.services import CAPACIDADES
        self.assertEqual({estado.value for estado in CAPACIDADES}, set(Equipo.Estado.values))

    def test_interno_entra_a_mantencion_pero_no_se_arrienda(self):
        from flota.services import puedeArrendarse, puedeEntrarAMantencion
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-INT', estado=Equipo.Estado.INTERNO)
        self.assertTrue(puedeEntrarAMantencion(equipo))
        self.assertFalse(puedeArrendarse(equipo))

    def test_en_faena_no_entra_a_mantencion(self):
        from flota.services import puedeEntrarAMantencion
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-FAE', estado=Equipo.Estado.EN_FAENA)
        self.assertFalse(puedeEntrarAMantencion(equipo))


class CambiarEstadoViewTest(TestCase):
    """El botón del inventario cambia el estado del equipo."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.client.force_login(self.usuario)

    def test_cambia_el_estado(self):
        response = self.client.post(
            reverse('flota:cambiar_estado', args=[self.equipo.id]),
            {'estado': Equipo.Estado.INTERNO},
        )
        self.assertRedirects(response, reverse('flota:equipos'))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.INTERNO)

    def test_un_estado_invalido_no_rompe(self):
        self.client.post(reverse('flota:cambiar_estado', args=[self.equipo.id]), {'estado': 'ROTO'})
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.DISPONIBLE)

    def test_el_inventario_ofrece_el_boton(self):
        response = self.client.get(reverse('flota:equipos'))
        self.assertContains(response, reverse('flota:cambiar_estado', args=[self.equipo.id]))
