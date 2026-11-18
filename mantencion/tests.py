from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from django.utils.formats import localize

from cuentas.models import Rol, Usuario
from flota.models import Equipo, TipoEquipo
from insumos.models import Insumo
from mantencion.models import (
    OrdenTrabajo,
    OrdenTrabajoInsumo,
    PlanMantencion,
    ServicioPlan,
    ServicioPlanInsumo,
)
from mantencion.services import CalculadoraProximoServicio


class CalculadoraProximoServicioTest(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Generador')
        self.servicio_250 = ServicioPlan.objects.create(plan=self.plan, nombre='250h', intervalo_horas=250)
        self.servicio_500 = ServicioPlan.objects.create(plan=self.plan, nombre='500h', intervalo_horas=500)

    def test_proximo_servicio_sin_mantenciones(self):
        calc = CalculadoraProximoServicio(umbral_alerta_horas=100)
        self.assertEqual(calc.calcularProximoServicio(self.equipo), self.servicio_250)

    def test_horas_restantes_descuenta_ultimo_cierre(self):
        OrdenTrabajo.objects.create(
            equipo=self.equipo,
            servicio_plan=self.servicio_250,
            tipo=OrdenTrabajo.Tipo.PREVENTIVA,
            estado=OrdenTrabajo.Estado.CERRADA,
            numero_ot='OT-001',
            horometro_cierre=Decimal('200.0'),
        )
        self.equipo.actualizarHorometro(Decimal('300.0'))
        calc = CalculadoraProximoServicio(umbral_alerta_horas=100)
        self.assertEqual(calc.horasRestantes(self.equipo, self.servicio_250), Decimal('150.0'))

    def test_esta_en_alerta(self):
        self.equipo.actualizarHorometro(Decimal('220.0'))
        calc = CalculadoraProximoServicio(umbral_alerta_horas=100)
        self.assertTrue(calc.estaEnAlerta(self.equipo))


class OrdenTrabajoTest(TestCase):
    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.insumo = Insumo.objects.create(codigo='INS-001', nombre='Filtro', unidad_medida='unidad')

    def test_cerrar_ot_asigna_estado_y_fecha(self):
        ot = OrdenTrabajo.objects.create(
            equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-002'
        )
        ot.cerrar(Decimal('350.0'))
        ot.refresh_from_db()
        self.assertEqual(ot.estado, OrdenTrabajo.Estado.CERRADA)
        self.assertEqual(ot.horometro_cierre, Decimal('350.0'))
        self.assertIsNotNone(ot.fecha_ejecucion)

    def test_registrar_insumo(self):
        ot = OrdenTrabajo.objects.create(
            equipo=self.equipo, tipo=OrdenTrabajo.Tipo.CORRECTIVA, numero_ot='OT-003'
        )
        detalle = ot.registrarInsumo(self.insumo, Decimal('2.00'), notas='cambio')
        self.assertEqual(OrdenTrabajoInsumo.objects.count(), 1)
        self.assertEqual(detalle.insumo, self.insumo)

    def test_servicios_ordenados(self):
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Generador')
        ServicioPlan.objects.create(plan=plan, nombre='500h', intervalo_horas=500)
        ServicioPlan.objects.create(plan=plan, nombre='250h', intervalo_horas=250)
        orden = plan.serviciosOrdenados()
        self.assertEqual([s.intervalo_horas for s in orden], [250, 500])

    def test_insumos_requeridos(self):
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Generador')
        servicio = ServicioPlan.objects.create(plan=plan, nombre='250h', intervalo_horas=250)
        ServicioPlanInsumo.objects.create(
            servicio_plan=servicio, insumo=self.insumo, cantidad=Decimal('1.00')
        )
        self.assertEqual(len(servicio.insumosRequeridos()), 1)


class OrdenesTrabajoViewsTest(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.insumo = Insumo.objects.create(codigo='INS-001', nombre='Filtro', unidad_medida='unidad')
        self.client.force_login(self.usuario)

    def test_crear_orden_genera_numero(self):
        response = self.client.post(reverse('mantencion:crear_orden'), {
            'equipo': self.equipo.id,
            'tipo': OrdenTrabajo.Tipo.PREVENTIVA,
            'servicio_plan': '',
            'fecha_programada': '',
            'observaciones': '',
        })
        orden = OrdenTrabajo.objects.get()
        self.assertEqual(orden.numero_ot, f'OT-{orden.id:04d}')
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))

    def test_registrar_insumo(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-010')
        response = self.client.post(reverse('mantencion:registrar_insumo', args=[orden.id]), {
            'insumo': self.insumo.id,
            'cantidad_usada': '2.00',
            'notas': 'cambio',
        })
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))
        self.assertEqual(OrdenTrabajoInsumo.objects.count(), 1)

    def test_cerrar_orden(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-011')
        orden.iniciar()
        response = self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {
            'horometro_cierre': '350.0',
        })
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.CERRADA)

    def test_cerrar_orden_deja_la_lectura_del_tecnico(self):
        """Cerrar es el momento en que el dato real entra: queda lectura y se mueve el equipo."""
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-012')
        orden.iniciar()
        self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {
            'horometro_cierre': '350.0',
        })
        lectura = self.equipo.lecturas.get()
        self.assertEqual(lectura.valor, Decimal('350.0'))
        self.assertEqual(lectura.fuente, 'TECNICO')
        self.assertEqual(lectura.usuario, self.usuario)
        self.assertTrue(lectura.validada)
        self.assertEqual(lectura.observacion, 'Cierre OT-012')
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.horometro_actual, Decimal('350.0'))

    def test_cerrar_orden_rechaza_horometro_menor_al_actual(self):
        """El horómetro no retrocede: un cierre con lectura menor no pasa."""
        self.equipo.actualizarHorometro(Decimal('400.0'))
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-013')
        orden.iniciar()
        response = self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {
            'horometro_cierre': '350.0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form_cierre'],
            'horometro_cierre',
            'El horómetro de cierre no puede ser menor al horómetro actual del equipo.',
        )
        self.assertContains(response, 'data-abrir-al-cargar="si"')
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.EN_CURSO)
        self.assertIsNone(orden.horometro_cierre)
        self.assertEqual(self.equipo.lecturas.count(), 0)
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.horometro_actual, Decimal('400.0'))

    def test_el_cierre_vive_en_un_dialogo(self):
        """El cierre se resuelve en la ficha, y el diálogo avisa el horómetro actual."""
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-014')
        orden.iniciar()
        response = self.client.get(reverse('mantencion:detalle_orden', args=[orden.id]))
        self.assertContains(response, 'id="dialogo-cerrar-orden"')
        self.assertContains(response, 'data-abrir-cierre')
        self.assertContains(response, f'Horómetro actual: {localize(self.equipo.horometro_actual)}')
        self.assertNotContains(response, 'data-abrir-al-cargar="si"')

    def test_la_lista_abre_el_dialogo_de_cierre(self):
        """El botón Cerrar de la lista llega a la ficha con el diálogo ya abierto."""
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-015')
        orden.iniciar()
        response = self.client.get(reverse('mantencion:detalle_orden', args=[orden.id]) + '?cerrar=1')
        self.assertContains(response, 'data-abrir-al-cargar="si"')

    def test_iniciar_orden(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-030')
        response = self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]))
        self.assertRedirects(response, reverse('mantencion:ordenes_trabajo'))
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.EN_CURSO)

    def test_cerrar_requiere_estar_en_curso(self):
        """Una PROGRAMADA primero se inicia; no se cierra de un salto."""
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-031')
        response = self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {
            'horometro_cierre': '350.0',
        })
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.PROGRAMADA)

    def test_iniciar_solo_desde_programada(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-032')
        orden.cerrar(Decimal('350.0'))
        self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]))
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.CERRADA)

    def test_el_alta_vive_en_un_dialogo(self):
        response = self.client.get(reverse('mantencion:ordenes_trabajo'))
        self.assertContains(response, 'id="dialogo-crear-orden"')
        self.assertContains(response, 'data-abrir-orden')
        self.assertNotContains(response, 'data-abrir-al-cargar="si"')

    def test_un_alta_rechazada_reabre_el_dialogo(self):
        response = self.client.post(reverse('mantencion:crear_orden'), {
            'equipo': self.equipo.id,
            'servicio_plan': '',
            'tipo': 'TIPO_INVALIDO',
            'fecha_programada': '',
            'observaciones': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-abrir-al-cargar="si"')

    def test_editar_orden(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-020')
        response = self.client.post(reverse('mantencion:editar_orden', args=[orden.id]), {
            'equipo': self.equipo.id,
            'servicio_plan': '',
            'tipo': OrdenTrabajo.Tipo.CORRECTIVA,
            'fecha_programada': '',
            'observaciones': 'corregida',
        })
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))
        orden.refresh_from_db()
        self.assertEqual(orden.tipo, OrdenTrabajo.Tipo.CORRECTIVA)
        self.assertEqual(orden.observaciones, 'corregida')

    def test_borrar_orden(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-021')
        response = self.client.post(reverse('mantencion:borrar_orden', args=[orden.id]))
        self.assertRedirects(response, reverse('mantencion:ordenes_trabajo'))
        self.assertFalse(OrdenTrabajo.objects.filter(pk=orden.pk).exists())

    def test_borrar_solo_acepta_post(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-022')
        self.assertEqual(
            self.client.get(reverse('mantencion:borrar_orden', args=[orden.id])).status_code,
            405,
        )

    def test_una_cerrada_no_se_edita(self):
        """Una vez cerrada es historial: el pronóstico no se cambia hacia atrás."""
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-023')
        orden.cerrar(Decimal('350.0'))
        response = self.client.post(reverse('mantencion:editar_orden', args=[orden.id]), {
            'equipo': self.equipo.id,
            'servicio_plan': '',
            'tipo': OrdenTrabajo.Tipo.CORRECTIVA,
            'fecha_programada': '',
            'observaciones': 'no debería',
        })
        self.assertRedirects(response, reverse('mantencion:detalle_orden', args=[orden.id]))
        orden.refresh_from_db()
        self.assertEqual(orden.tipo, OrdenTrabajo.Tipo.PREVENTIVA)

    def test_una_cerrada_no_se_borra(self):
        orden = OrdenTrabajo.objects.create(equipo=self.equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-024')
        orden.cerrar(Decimal('350.0'))
        self.client.post(reverse('mantencion:borrar_orden', args=[orden.id]))
        self.assertTrue(OrdenTrabajo.objects.filter(pk=orden.pk).exists())


class PlanesViewsTest(TestCase):
    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Base')
        self.client.force_login(self.usuario)

    def test_crear_plan(self):
        response = self.client.post(reverse('mantencion:crear_plan'), {
            'tipo_equipo': self.tipo.id,
            'nombre': 'Plan Nuevo',
        })
        self.assertRedirects(response, reverse('mantencion:planes'))
        self.assertTrue(PlanMantencion.objects.filter(nombre='Plan Nuevo').exists())

    def test_crear_servicio(self):
        response = self.client.post(reverse('mantencion:crear_servicio'), {
            'plan': self.plan.id,
            'nombre': '1000h',
            'intervalo_horas': '1000',
            'descripcion': '',
        })
        self.assertRedirects(response, reverse('mantencion:planes'))
        self.assertTrue(ServicioPlan.objects.filter(nombre='1000h').exists())

    def test_editar_plan(self):
        response = self.client.post(reverse('mantencion:editar_plan', args=[self.plan.id]), {
            'tipo_equipo': self.tipo.id,
            'nombre': 'Plan Renombrado',
        })
        self.assertRedirects(response, reverse('mantencion:planes'))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.nombre, 'Plan Renombrado')

    def test_editar_servicio(self):
        servicio = ServicioPlan.objects.create(plan=self.plan, nombre='250h', intervalo_horas=250)
        response = self.client.post(reverse('mantencion:editar_servicio', args=[servicio.id]), {
            'plan': self.plan.id,
            'nombre': '300h',
            'intervalo_horas': '300',
            'descripcion': '',
        })
        self.assertRedirects(response, reverse('mantencion:planes'))
        servicio.refresh_from_db()
        self.assertEqual(servicio.intervalo_horas, 300)

    def test_borrar_plan_sin_servicios(self):
        response = self.client.post(reverse('mantencion:borrar_plan', args=[self.plan.id]))
        self.assertRedirects(response, reverse('mantencion:planes'))
        self.assertFalse(PlanMantencion.objects.filter(pk=self.plan.pk).exists())

    def test_un_plan_con_servicios_no_se_borra(self):
        ServicioPlan.objects.create(plan=self.plan, nombre='250h', intervalo_horas=250)
        self.client.post(reverse('mantencion:borrar_plan', args=[self.plan.id]))
        self.assertTrue(PlanMantencion.objects.filter(pk=self.plan.pk).exists())

    def test_borrar_servicio_sin_ots(self):
        servicio = ServicioPlan.objects.create(plan=self.plan, nombre='250h', intervalo_horas=250)
        response = self.client.post(reverse('mantencion:borrar_servicio', args=[servicio.id]))
        self.assertRedirects(response, reverse('mantencion:planes'))
        self.assertFalse(ServicioPlan.objects.filter(pk=servicio.pk).exists())

    def test_un_servicio_con_ots_no_se_borra(self):
        servicio = ServicioPlan.objects.create(plan=self.plan, nombre='250h', intervalo_horas=250)
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-X')
        OrdenTrabajo.objects.create(
            equipo=equipo, servicio_plan=servicio, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot='OT-X'
        )
        self.client.post(reverse('mantencion:borrar_servicio', args=[servicio.id]))
        self.assertTrue(ServicioPlan.objects.filter(pk=servicio.pk).exists())


class OrdenTrabajoServicioDelTipoTest(TestCase):
    """Defecto hallado en la prueba manual M5: el servicio debe ser del tipo del equipo."""

    def setUp(self):
        from flota.models import Equipo, TipoEquipo
        from mantencion.forms import OrdenTrabajoForm
        self.Form = OrdenTrabajoForm
        self.grua = TipoEquipo.objects.create(nombre='Grúa', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.gen = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.grua, codigo='V1')
        self.servicio_grua = ServicioPlan.objects.create(
            plan=PlanMantencion.objects.create(tipo_equipo=self.grua, nombre='Plan Grúa'),
            nombre='500 HORAS', intervalo_horas=500)
        self.servicio_gen = ServicioPlan.objects.create(
            plan=PlanMantencion.objects.create(tipo_equipo=self.gen, nombre='Plan Gen'),
            nombre='500 HORAS', intervalo_horas=500)

    def _datos(self, servicio):
        return {'equipo': self.equipo.pk, 'servicio_plan': servicio.pk, 'tipo': OrdenTrabajo.Tipo.PREVENTIVA,
                'fecha_programada': '2026-10-20', 'observaciones': ''}

    def test_rechaza_servicio_de_otro_tipo_de_equipo(self):
        form = self.Form(self._datos(self.servicio_gen))
        self.assertFalse(form.is_valid())
        self.assertIn('servicio_plan', form.errors)

    def test_acepta_servicio_del_mismo_tipo(self):
        self.assertTrue(self.Form(self._datos(self.servicio_grua)).is_valid())


class ProximosServiciosEnBloqueTest(TestCase):
    """La versión en bloque da el mismo resultado que la individual y usa pocas consultas."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan')
        self.s250 = ServicioPlan.objects.create(plan=plan, nombre='250h', intervalo_horas=250)
        self.s500 = ServicioPlan.objects.create(plan=plan, nombre='500h', intervalo_horas=500)
        self.equipos = []
        for i in range(6):
            e = Equipo.objects.create(tipo_equipo=self.tipo, codigo=f'E{i}')
            e.actualizarHorometro(Decimal(100 * (i + 1)))
            OrdenTrabajo.objects.create(
                equipo=e, servicio_plan=self.s250 if i % 2 else self.s500, tipo=OrdenTrabajo.Tipo.PREVENTIVA,
                estado=OrdenTrabajo.Estado.CERRADA, numero_ot=f'OT-{i}', horometro_cierre=Decimal(50 * i))
            self.equipos.append(e)
        self.sin_plan = Equipo.objects.create(
            tipo_equipo=TipoEquipo.objects.create(nombre='Sin plan', unidad_medida=TipoEquipo.UnidadMedida.HORAS), codigo='X')

    def test_resultado_igual_al_individual(self):
        calc = CalculadoraProximoServicio(umbral_alerta_horas=100)
        todos = self.equipos + [self.sin_plan]
        bloque = calc.proximosServicios(todos)
        for e in todos:
            proximo = calc.calcularProximoServicio(e)
            horas = calc.horasRestantes(e, proximo) if proximo else None
            self.assertEqual(bloque[e.id], (proximo, horas), e.codigo)

    def test_cantidad_de_consultas_no_depende_de_la_flota(self):
        calc = CalculadoraProximoServicio(umbral_alerta_horas=100)
        with self.assertNumQueries(2):
            calc.proximosServicios(self.equipos)


class InicioDeOrdenPorEstadoTest(TestCase):
    """Una OT solo arranca si el equipo puede entrar al taller, y lo manda ahí."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.client.force_login(self.usuario)

    def _orden(self, estado):
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo=f'EQ-{estado}', estado=estado)
        return OrdenTrabajo.objects.create(
            equipo=equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot=f'OT-{estado}'
        )

    def test_iniciar_manda_el_equipo_a_mantencion(self):
        orden = self._orden(Equipo.Estado.DISPONIBLE)
        self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]))
        orden.refresh_from_db()
        orden.equipo.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.EN_CURSO)
        self.assertEqual(orden.equipo.estado, Equipo.Estado.EN_MANTENIMIENTO)
        self.assertEqual(orden.equipo.estado_previo, Equipo.Estado.DISPONIBLE)

    def test_iniciar_desde_interno_recuerda_el_origen(self):
        orden = self._orden(Equipo.Estado.INTERNO)
        self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]))
        orden.equipo.refresh_from_db()
        self.assertEqual(orden.equipo.estado, Equipo.Estado.EN_MANTENIMIENTO)
        self.assertEqual(orden.equipo.estado_previo, Equipo.Estado.INTERNO)

    def test_no_inicia_si_el_equipo_esta_en_faena(self):
        orden = self._orden(Equipo.Estado.EN_FAENA)
        response = self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]), follow=True)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.PROGRAMADA)
        self.assertContains(response, 'sigue en faena')

    def test_no_inicia_si_el_equipo_ya_esta_en_mantencion(self):
        orden = self._orden(Equipo.Estado.EN_MANTENIMIENTO)
        response = self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]), follow=True)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, OrdenTrabajo.Estado.PROGRAMADA)
        self.assertContains(response, 'ya está en mantenimiento')


class CierreDevuelveElEquipoTest(TestCase):
    """Cerrar la OT devuelve el equipo al estado del que vino."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.client.force_login(self.usuario)

    def _orden_en_curso(self, estado):
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo=f'EQ-{estado}', estado=estado)
        orden = OrdenTrabajo.objects.create(
            equipo=equipo, tipo=OrdenTrabajo.Tipo.PREVENTIVA, numero_ot=f'OT-{estado}'
        )
        self.client.post(reverse('mantencion:iniciar_orden', args=[orden.id]))
        return orden

    def test_cerrar_devuelve_el_equipo_a_interno(self):
        orden = self._orden_en_curso(Equipo.Estado.INTERNO)
        self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {'horometro_cierre': '100.0'})
        orden.equipo.refresh_from_db()
        self.assertEqual(orden.equipo.estado, Equipo.Estado.INTERNO)

    def test_cerrar_devuelve_el_equipo_a_disponible(self):
        orden = self._orden_en_curso(Equipo.Estado.DISPONIBLE)
        self.client.post(reverse('mantencion:cerrar_orden', args=[orden.id]), {'horometro_cierre': '100.0'})
        orden.equipo.refresh_from_db()
        self.assertEqual(orden.equipo.estado, Equipo.Estado.DISPONIBLE)


class ExportacionOrdenesTest(TestCase):
    """La planilla de órdenes trae los datos y respeta el filtro de abiertas."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='otexcel@vilas.cl', password='test1234', nombre='OT Excel')
        self.client.force_login(self.usuario)
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.abierta = OrdenTrabajo.objects.create(
            equipo=self.equipo, tipo='PREVENTIVA', numero_ot='1001',
            estado=OrdenTrabajo.Estado.PROGRAMADA,
        )
        self.cerrada = OrdenTrabajo.objects.create(
            equipo=self.equipo, tipo='CORRECTIVA', numero_ot='1002',
            estado=OrdenTrabajo.Estado.CERRADA,
        )

    def _hoja(self, respuesta):
        return load_workbook(BytesIO(respuesta.content)).active

    def test_exportar_ordenes_devuelve_un_xlsx(self):
        respuesta = self.client.get(reverse('mantencion:exportar_ordenes'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('spreadsheetml', respuesta['Content-Type'])
        self.assertIn('attachment', respuesta['Content-Disposition'])

        hoja = self._hoja(respuesta)
        self.assertEqual(hoja['A1'].value, 'N° OT')
        self.assertEqual(hoja.max_row, 3)

    def test_exportar_ordenes_respeta_el_filtro_de_abiertas(self):
        respuesta = self.client.get(
            reverse('mantencion:exportar_ordenes'), {'estado': 'ABIERTAS'}
        )
        hoja = self._hoja(respuesta)

        self.assertEqual(hoja.max_row, 2)
        self.assertEqual(hoja['A2'].value, '1001')

    def test_otro_rol_no_puede_exportar_ni_ve_el_boton(self):
        rol, _ = Rol.objects.get_or_create(nombre='operador', defaults={'descripcion': 'Operador'})
        usuario = Usuario.objects.create_user(
            email='operador-ot@vilas.cl', password='test1234', nombre='Operador'
        )
        usuario.rol = rol
        usuario.email_verificado = True
        usuario.save(update_fields=['rol', 'email_verificado'])
        self.client.force_login(usuario)

        self.assertEqual(
            self.client.get(reverse('mantencion:exportar_ordenes')).status_code, 403
        )
        self.assertNotContains(
            self.client.get(reverse('mantencion:ordenes_trabajo')),
            reverse('mantencion:exportar_ordenes'),
        )


class PronosticoMantencionTest(TestCase):
    """Próxima mantención por equipo: horómetro en que toca y horas que faltan."""

    def setUp(self):
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Generador')
        self.servicio_250 = ServicioPlan.objects.create(plan=plan, nombre='Servicio 250h', intervalo_horas=250)
        self.servicio_500 = ServicioPlan.objects.create(plan=plan, nombre='Servicio 500h', intervalo_horas=500)

    def _pronostico(self, equipo=None):
        from mantencion.services import pronosticoMantencion

        equipo = equipo or Equipo.objects.get(pk=self.equipo.pk)
        return pronosticoMantencion([equipo])[equipo.id]

    def test_al_dia_calcula_horometro_objetivo_y_horas_restantes(self):
        self.equipo.actualizarHorometro(Decimal('100.0'))
        p = self._pronostico()
        self.assertEqual(p['servicio'], self.servicio_250)
        self.assertEqual(p['horas_restantes'], Decimal('150.0'))
        self.assertEqual(p['horometro_objetivo'], Decimal('250.0'))
        self.assertEqual(p['alerta'], 'AL_DIA')

    def test_el_objetivo_parte_desde_el_ultimo_cierre(self):
        OrdenTrabajo.objects.create(
            equipo=self.equipo, servicio_plan=self.servicio_250, tipo=OrdenTrabajo.Tipo.PREVENTIVA,
            estado=OrdenTrabajo.Estado.CERRADA, numero_ot='OT-001', horometro_cierre=Decimal('200.0'),
        )
        self.equipo.actualizarHorometro(Decimal('300.0'))
        p = self._pronostico()
        self.assertEqual(p['servicio'], self.servicio_250)
        self.assertEqual(p['horometro_objetivo'], Decimal('450.0'))
        self.assertEqual(p['horas_restantes'], Decimal('150.0'))

    def test_por_vencer_dentro_del_umbral(self):
        self.equipo.actualizarHorometro(Decimal('220.0'))
        p = self._pronostico()
        self.assertEqual(p['alerta'], 'POR_VENCER')
        self.assertEqual(p['horas_restantes'], Decimal('30.0'))

    def test_vencido_informa_horas_de_atraso(self):
        self.equipo.actualizarHorometro(Decimal('300.0'))
        p = self._pronostico()
        self.assertEqual(p['alerta'], 'VENCIDO')
        self.assertEqual(p['horas_vencidas'], Decimal('50.0'))

    def test_tipo_sin_plan(self):
        otro = TipoEquipo.objects.create(nombre='Compresor', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        equipo = Equipo.objects.create(tipo_equipo=otro, codigo='CMP-001')
        p = self._pronostico(equipo)
        self.assertEqual(p['alerta'], 'SIN_PLAN')
        self.assertIsNone(p['servicio'])
        self.assertIsNone(p['horometro_objetivo'])

    def test_lista_y_ficha_muestran_las_columnas(self):
        self.equipo.actualizarHorometro(Decimal('100.0'))
        self.client.force_login(self.usuario)
        lista = self.client.get(reverse('flota:equipos'))
        self.assertContains(lista, 'Siguiente mantención')
        self.assertContains(lista, 'Próxima mantención')
        self.assertContains(lista, 'Servicio 250h')
        self.assertEqual(lista.context['equipos'][0].mantencion['horas_restantes'], Decimal('150.0'))
        ficha = self.client.get(reverse('flota:detalle_equipo', args=[self.equipo.pk]))
        self.assertContains(ficha, 'Siguiente mantención')
        self.assertContains(ficha, 'cada 250 h')


class ModificarMantencionTest(TestCase):
    """Botón "Modificar mantención" en la lista de equipos y la pantalla del plan."""

    def setUp(self):
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.sin_plan = TipoEquipo.objects.create(nombre='Compresor', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.plan = PlanMantencion.objects.create(tipo_equipo=self.tipo, nombre='Plan Generador')
        ServicioPlan.objects.create(plan=self.plan, nombre='Servicio 250h', intervalo_horas=250)
        Equipo.objects.create(tipo_equipo=self.tipo, codigo='GEN-001')
        Equipo.objects.create(tipo_equipo=self.sin_plan, codigo='COM-001')
        self.client.force_login(self.usuario)

    def test_la_lista_enlaza_el_plan_del_tipo(self):
        respuesta = self.client.get(reverse('flota:equipos'))
        self.assertContains(respuesta, 'Modificar mantención', count=2)
        self.assertContains(respuesta, reverse('mantencion:editar_plan', args=[self.plan.id]) + '?desde=equipos')
        self.assertContains(respuesta, reverse('mantencion:crear_plan') + f'?tipo_equipo={self.sin_plan.id}')

    def test_un_rol_sin_permiso_no_ve_el_boton(self):
        consulta = Rol.objects.create(nombre='consulta', descripcion='Solo lectura')
        self.usuario.rol = consulta
        self.usuario.save(update_fields=['rol'])
        respuesta = self.client.get(reverse('flota:equipos'))
        self.assertNotContains(respuesta, 'Modificar mantención')

    def test_la_pantalla_del_plan_muestra_sus_servicios(self):
        respuesta = self.client.get(reverse('mantencion:editar_plan', args=[self.plan.id]) + '?desde=equipos')
        self.assertContains(respuesta, 'Servicio 250h')
        self.assertContains(respuesta, 'Agregar servicio')
        self.assertContains(respuesta, 'Intervalo (h)')

    def test_guardar_desde_equipos_vuelve_a_la_lista(self):
        respuesta = self.client.post(reverse('mantencion:editar_plan', args=[self.plan.id]), {
            'tipo_equipo': self.tipo.id, 'nombre': 'Plan Generador v2', 'desde': 'equipos',
        })
        self.assertRedirects(respuesta, reverse('flota:equipos'))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.nombre, 'Plan Generador v2')

    def test_crear_plan_llega_con_el_tipo_elegido(self):
        respuesta = self.client.get(reverse('mantencion:crear_plan') + f'?tipo_equipo={self.sin_plan.id}')
        self.assertEqual(respuesta.context['form'].initial['tipo_equipo'], str(self.sin_plan.id))
