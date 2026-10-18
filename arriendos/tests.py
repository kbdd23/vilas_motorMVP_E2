from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arriendos.forms import ArriendoForm
from arriendos.models import Arriendo
from cuentas.models import Cliente, Rol, Usuario
from flota.models import Equipo, TipoEquipo


class ArriendoTest(TestCase):
    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )

    def test_vigente_cuando_abierto(self):
        self.assertTrue(self.arriendo.estaVigente())

    def test_no_vigente_al_cerrar(self):
        """Cerrar el contrato es fijar la fecha de término: deja de estar vigente."""
        self.arriendo.cerrar(timezone.localdate() - timedelta(days=1))
        self.arriendo.refresh_from_db()
        self.assertFalse(self.arriendo.estaVigente())

    def test_no_vigente_con_fecha_de_termino_futura(self):
        """Aunque la fecha de término sea futura, el contrato ya se cerró."""
        self.arriendo.cerrar(timezone.localdate() + timedelta(days=10))
        self.arriendo.refresh_from_db()
        self.assertFalse(self.arriendo.estaVigente())

    def test_queryset_vigentes(self):
        self.arriendo.cerrar(timezone.localdate())
        self.assertEqual(Arriendo.objects.vigentes().count(), 0)
        Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        self.assertEqual(Arriendo.objects.vigentes().count(), 1)


class ArriendosViewsTest(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.client.force_login(self.usuario)

    def _post_arriendo(self):
        return self.client.post(reverse('arriendos:crear_arriendo'), {
            'equipo': self.equipo.id,
            'cliente': self.cliente.id,
            'fecha_inicio': timezone.localdate().isoformat(),
        })

    def test_crear_arriendo(self):
        response = self._post_arriendo()
        self.assertRedirects(response, reverse('arriendos:arriendos'))
        self.assertEqual(Arriendo.objects.count(), 1)

    def test_crear_arriendo_pasa_el_equipo_a_faena(self):
        self._post_arriendo()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.EN_FAENA)

    def test_crear_arriendo_rechaza_equipo_vigente(self):
        Arriendo.objects.create(equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate())
        response = self._post_arriendo()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Arriendo.objects.count(), 1)
        self.assertContains(response, 'ya tiene un arriendo vigente')

    def test_crear_arriendo_rechaza_equipo_no_disponible(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        response = self._post_arriendo()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Arriendo.objects.count(), 0)
        self.assertContains(response, 'no está disponible')

    def test_flujo_cerrar_marcar_disponible_y_volver_a_arrendar(self):
        """El ciclo completo: arrendar, cerrar, marcar disponible y re-arrendar."""
        self._post_arriendo()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.EN_FAENA)

        arriendo = Arriendo.objects.get()
        self.client.post(reverse('arriendos:cerrar_arriendo', args=[arriendo.id]), {
            'fecha_termino': timezone.localdate().isoformat(),
        })
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.EN_FAENA)

        self.client.post(reverse('flota:marcar_disponible', args=[self.equipo.id]))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.Estado.DISPONIBLE)

        response = self._post_arriendo()
        self.assertRedirects(response, reverse('arriendos:arriendos'))
        self.assertEqual(Arriendo.objects.count(), 2)

    def test_cerrar_arriendo(self):
        arriendo = Arriendo.objects.create(equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate())
        fecha = (timezone.localdate() + timedelta(days=5)).isoformat()
        response = self.client.post(reverse('arriendos:cerrar_arriendo', args=[arriendo.id]), {
            'fecha_termino': fecha,
        })
        self.assertRedirects(response, reverse('arriendos:arriendos'))
        arriendo.refresh_from_db()
        self.assertIsNotNone(arriendo.fecha_termino)


class ArriendosListadoTest(TestCase):
    """El botón de marcar disponible vive en la columna Acción del listado."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.client.force_login(self.usuario)

    def test_arriendo_vigente_muestra_cerrar(self):
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        response = self.client.get(reverse('arriendos:arriendos'))
        self.assertContains(response, reverse('arriendos:cerrar_arriendo', args=[arriendo.id]))
        self.assertNotContains(response, 'Marcar disponible')

    def test_arriendo_cerrado_con_equipo_en_faena_muestra_marcar_disponible(self):
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        arriendo.cerrar(timezone.localdate())
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        response = self.client.get(reverse('arriendos:arriendos'))
        self.assertContains(response, 'Marcar disponible')

    def test_arriendo_cerrado_con_equipo_disponible_no_muestra_accion(self):
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        arriendo.cerrar(timezone.localdate())
        response = self.client.get(reverse('arriendos:arriendos'))
        self.assertNotContains(response, reverse('arriendos:cerrar_arriendo', args=[arriendo.id]))
        self.assertNotContains(response, 'Marcar disponible')

    def test_arriendo_cerrado_no_ofrece_marcar_disponible_si_el_equipo_volvio_a_arrendarse(self):
        """Con otro contrato vigente la máquina sigue comprometida: no hay nada que marcar."""
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        arriendo.cerrar(timezone.localdate())
        Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=timezone.localdate()
        )
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        response = self.client.get(reverse('arriendos:arriendos'))
        self.assertNotContains(response, 'Marcar disponible')


class ArriendoFormTest(TestCase):
    """El desplegable solo ofrece equipos disponibles."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )

    def test_solo_ofrece_equipos_disponibles(self):
        disponible = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-DISP')
        en_faena = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-FAENA')
        en_faena.cambiarEstado(Equipo.Estado.EN_FAENA)

        queryset = ArriendoForm().fields['equipo'].queryset

        self.assertIn(disponible, queryset)
        self.assertNotIn(en_faena, queryset)

    def test_no_ofrece_un_equipo_en_mantenimiento(self):
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-MANT')
        equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)

        self.assertNotIn(equipo, ArriendoForm().fields['equipo'].queryset)


class BandejaArriendosTest(TestCase):
    """La bandeja lista solo los contratos que tienen un paso pendiente."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.client.force_login(self.usuario)

    def _equipos_en_bandeja(self, **parametros):
        response = self.client.get(reverse('arriendos:arriendos'), parametros)
        return [arriendo.equipo.codigo for arriendo in response.context['arriendos']]

    def _arriendo(self, dias_de_inicio=0):
        return Arriendo.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            fecha_inicio=timezone.localdate() - timedelta(days=dias_de_inicio),
        )

    def test_arriendo_vigente_siempre_aparece(self):
        self._arriendo(dias_de_inicio=400)
        self.assertIn('EQ-001', self._equipos_en_bandeja())

    def test_cierre_antiguo_sin_marcar_el_regreso_sigue_en_la_bandeja(self):
        """El reloj no limpia un paso pendiente: falta marcar el regreso."""
        arriendo = self._arriendo(dias_de_inicio=400)
        arriendo.cerrar(timezone.localdate() - timedelta(days=300))
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)

        self.assertIn('EQ-001', self._equipos_en_bandeja())

    def test_cierre_resuelto_desaparece_al_vencer_la_ventana(self):
        arriendo = self._arriendo(dias_de_inicio=10)
        arriendo.cerrar(timezone.localdate() - timedelta(days=5))

        self.assertNotIn('EQ-001', self._equipos_en_bandeja())

    def test_cierre_resuelto_de_hoy_sigue_visible(self):
        arriendo = self._arriendo()
        arriendo.cerrar(timezone.localdate())

        self.assertIn('EQ-001', self._equipos_en_bandeja())

    def test_ventana_amplia_recupera_cierres_antiguos(self):
        arriendo = self._arriendo(dias_de_inicio=10)
        arriendo.cerrar(timezone.localdate() - timedelta(days=5))

        self.assertNotIn('EQ-001', self._equipos_en_bandeja())
        self.assertIn('EQ-001', self._equipos_en_bandeja(ventana='168'))

    def test_ventana_invalida_usa_la_por_defecto(self):
        arriendo = self._arriendo(dias_de_inicio=10)
        arriendo.cerrar(timezone.localdate() - timedelta(days=5))

        self.assertNotIn('EQ-001', self._equipos_en_bandeja(ventana='9999'))

    def test_una_sola_fila_por_equipo(self):
        primero = self._arriendo(dias_de_inicio=10)
        primero.cerrar(timezone.localdate() - timedelta(days=10))
        self._arriendo()
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)

        self.assertEqual(self._equipos_en_bandeja().count('EQ-001'), 1)
