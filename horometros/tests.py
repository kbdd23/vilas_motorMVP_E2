from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from arriendos.models import Arriendo
from cuentas.models import Cliente, Rol, Usuario
from flota.models import Equipo, TipoEquipo
from horometros.forms import SolicitudHorometroForm
from horometros.models import LecturaHorometro, SolicitudHorometro
from horometros.services import ValidadorDatos, arrendatarioDelEquipo, fuenteSugerida


class ValidadorDatosTest(TestCase):
    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-001', horometro_actual=Decimal('100.0')
        )
        self.validador = ValidadorDatos()

    def test_lectura_igual_o_mayor_es_valida(self):
        self.assertTrue(self.validador.validar(self.equipo, Decimal('100.0')))
        self.assertTrue(self.validador.validar(self.equipo, Decimal('120.0')))

    def test_lectura_menor_es_invalida(self):
        self.assertFalse(self.validador.validar(self.equipo, Decimal('99.9')))

    def test_lectura_negativa_es_invalida(self):
        self.assertFalse(self.validador.validar(self.equipo, Decimal('-5.0')))

    def test_valor_no_numerico_es_invalido(self):
        self.assertFalse(self.validador.validar(self.equipo, 'no-numero'))
        self.assertFalse(self.validador.validar(self.equipo, None))


class ServiciosDeHorometrosTest(TestCase):
    """Reglas de dominio: a quién se le pide el dato y qué fuente sugerir."""

    def setUp(self):
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.otro_cliente = Cliente.objects.create(rut='22222222-2', razon_social='Cliente Y')
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')

    def test_sin_arriendos_no_hay_arrendatario(self):
        self.assertIsNone(arrendatarioDelEquipo(self.equipo))

    def test_arrendatario_es_el_del_arriendo_mas_reciente(self):
        Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=date(2026, 1, 5)
        )
        Arriendo.objects.create(
            equipo=self.equipo, cliente=self.otro_cliente, fecha_inicio=date(2026, 3, 1)
        )
        self.assertEqual(arrendatarioDelEquipo(self.equipo), self.otro_cliente)

    def test_arriendo_cerrado_sigue_siendo_el_arrendatario(self):
        """La máquina puede no haber vuelto: el dato se le pide al que la tiene."""
        arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=date(2026, 1, 5)
        )
        arriendo.cerrar(date(2026, 6, 30))
        self.assertEqual(arrendatarioDelEquipo(self.equipo), self.cliente)

    def test_fuente_sugerida_segun_el_estado(self):
        self.equipo.cambiarEstado(Equipo.Estado.EN_FAENA)
        self.assertEqual(fuenteSugerida(self.equipo), 'CLIENTE')
        self.equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        self.assertEqual(fuenteSugerida(self.equipo), 'TECNICO')
        self.equipo.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        self.assertEqual(fuenteSugerida(self.equipo), 'TELEMETRIA')


class SolicitudHorometroFormTest(TestCase):
    """La fuente define de dónde salen los equipos."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.en_faena = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-FAENA', estado=Equipo.Estado.EN_FAENA
        )
        self.en_bodega = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-BODEGA', estado=Equipo.Estado.DISPONIBLE
        )
        self.en_taller = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-TALLER', estado=Equipo.Estado.EN_MANTENIMIENTO
        )

    def equipos_ofrecidos(self, **initial):
        return list(SolicitudHorometroForm(initial=initial).fields['equipo'].queryset)

    def test_sin_fuente_no_ofrece_equipos(self):
        """Primero hay que decidir a quién se le pide: eso define los equipos."""
        self.assertEqual(self.equipos_ofrecidos(), [])

    def test_la_fuente_arranca_sin_elegir(self):
        """La fuente no viene puesta: es la que decide qué equipos se ofrecen."""
        form = SolicitudHorometroForm()
        vacias = [opcion for opcion in form.fields['fuente'].choices if opcion[0] == '']
        self.assertEqual(vacias, [('', '— Elige una fuente —')])

    def test_la_fuente_vacia_no_pasa(self):
        form = SolicitudHorometroForm(data={'fuente': '', 'equipo': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('fuente', form.errors)

    def test_cliente_ofrece_solo_equipos_en_faena(self):
        self.assertEqual(self.equipos_ofrecidos(fuente='CLIENTE'), [self.en_faena])

    def test_tecnico_ofrece_solo_equipos_disponibles(self):
        self.assertEqual(self.equipos_ofrecidos(fuente='TECNICO'), [self.en_bodega])

    def test_telemetria_ofrece_cualquier_equipo(self):
        self.assertEqual(
            self.equipos_ofrecidos(fuente='TELEMETRIA'),
            [self.en_bodega, self.en_faena, self.en_taller],
        )

    def test_rechaza_un_equipo_que_no_corresponde_a_la_fuente(self):
        form = SolicitudHorometroForm(data={'fuente': 'CLIENTE', 'equipo': self.en_bodega.id})
        self.assertFalse(form.is_valid())
        self.assertIn('equipo', form.errors)

    def test_avisa_cuando_la_fuente_no_tiene_equipos(self):
        """Con todo en taller no hay a quién pedirle en faena: hay que explicarlo."""
        self.en_faena.cambiarEstado(Equipo.Estado.EN_MANTENIMIENTO)
        self.assertTrue(SolicitudHorometroForm(initial={'fuente': 'CLIENTE'}).sinEquipos())
        self.assertFalse(SolicitudHorometroForm(initial={'fuente': 'TELEMETRIA'}).sinEquipos())


class SolicitudHorometroTest(TestCase):
    """Ciclo de vida: nace pendiente y se cierra en un paso."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.tipo = TipoEquipo.objects.create(
            nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-001')
        self.solicitud = SolicitudHorometro.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            usuario_solicita=self.usuario,
            fuente='CLIENTE',
            fecha_solicitud=timezone.now(),
        )

    def test_nace_pendiente_y_sin_fecha_de_resolucion(self):
        self.assertTrue(self.solicitud.estaPendiente())
        self.assertIsNone(self.solicitud.fecha_resolucion)

    def test_una_solicitud_al_cliente_es_del_cliente(self):
        self.assertTrue(self.solicitud.esDelCliente())

    def test_el_estado_vencida_ya_no_existe(self):
        """Una solicitud se cierra con el dato o se borra: no hay tercer estado."""
        self.assertEqual(
            [estado for estado, _ in SolicitudHorometro.Estado.choices],
            ['PENDIENTE', 'CUMPLIDA'],
        )
        self.assertFalse(hasattr(SolicitudHorometro, 'marcarVencida'))

    def test_cumplir(self):
        lectura = LecturaHorometro.objects.create(
            equipo=self.equipo,
            usuario=self.usuario,
            valor=Decimal('150.0'),
            fecha_hora=timezone.now(),
            fuente=LecturaHorometro.Fuente.CLIENTE,
        )
        self.solicitud.cumplir(lectura)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudHorometro.Estado.CUMPLIDA)
        self.assertEqual(self.solicitud.lectura, lectura)
        self.assertIsNotNone(self.solicitud.fecha_resolucion)


class BandejaHorometrosTest(TestCase):
    """La bandeja y sus acciones: cada solicitud con un paso pendiente."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Planificador')
        self.cliente = Cliente.objects.create(rut='11111111-1', razon_social='Cliente X')
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.equipo = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-001',
            horometro_actual=Decimal('100.0'), estado=Equipo.Estado.EN_FAENA,
        )
        self.arriendo = Arriendo.objects.create(
            equipo=self.equipo, cliente=self.cliente, fecha_inicio=date(2026, 1, 5)
        )
        self.solicitud = SolicitudHorometro.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            usuario_solicita=self.usuario,
            fuente='CLIENTE',
            fecha_solicitud=timezone.now(),
        )
        self.client.force_login(self.usuario)

    def url_lectura(self):
        return reverse('horometros:registrar_lectura', args=[self.solicitud.id])

    def url_borrar(self):
        return reverse('horometros:borrar_solicitud', args=[self.solicitud.id])

    # --- Alta de solicitudes -------------------------------------------------

    def test_crear_solicitud_al_cliente_deriva_el_cliente(self):
        response = self.client.post(reverse('horometros:crear_solicitud'), {
            'fuente': 'CLIENTE',
            'equipo': self.equipo.id,
        })
        self.assertRedirects(response, reverse('horometros:index'))
        nueva = SolicitudHorometro.objects.latest('id')
        self.assertEqual(nueva.cliente, self.cliente)
        self.assertEqual(nueva.fuente, 'CLIENTE')

    def test_crear_solicitud_al_tecnico_no_tiene_cliente(self):
        """Al técnico no se le pide en nombre de nadie de afuera."""
        self.equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        response = self.client.post(reverse('horometros:crear_solicitud'), {
            'fuente': 'TECNICO',
            'equipo': self.equipo.id,
        })
        self.assertRedirects(response, reverse('horometros:index'))
        self.assertIsNone(SolicitudHorometro.objects.latest('id').cliente)

    def test_crear_solicitud_rechaza_un_equipo_de_otra_fuente(self):
        self.equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        response = self.client.post(reverse('horometros:crear_solicitud'), {
            'fuente': 'CLIENTE',
            'equipo': self.equipo.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SolicitudHorometro.objects.count(), 1)

    def test_la_bandeja_trae_el_formulario_de_alta(self):
        """El alta vive en un diálogo de la bandeja, no en una página aparte."""
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, 'id="dialogo-solicitud"')
        self.assertContains(response, 'data-abrir-solicitud')
        self.assertContains(response, '— Elige una fuente —')

    def test_la_bandeja_nace_con_los_dialogos_cerrados(self):
        response = self.client.get(reverse('horometros:index'))
        self.assertNotContains(response, 'data-abrir-al-cargar="si"')

    def test_la_url_de_alta_abre_el_dialogo(self):
        """El enlace directo al alta sigue sirviendo: abre el diálogo y no otra página."""
        response = self.client.get(reverse('horometros:crear_solicitud'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-abrir-al-cargar="si"')
        self.assertContains(response, 'id="dialogo-solicitud"')

    def test_un_post_de_alta_rechazado_reabre_su_dialogo(self):
        """El error tiene que quedar a la vista, no perderse detrás de la tabla."""
        self.equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        response = self.client.post(reverse('horometros:crear_solicitud'), {
            'fuente': 'CLIENTE',
            'equipo': self.equipo.id,
        })
        self.assertContains(response, 'data-abrir-al-cargar="si"')
        self.assertContains(response, 'Ese equipo no corresponde a la fuente elegida')
        self.assertEqual(SolicitudHorometro.objects.count(), 1)

    def test_crear_solicitud_al_cliente_sin_arriendo_avisa(self):
        self.arriendo.delete()
        response = self.client.post(reverse('horometros:crear_solicitud'), {
            'fuente': 'CLIENTE',
            'equipo': self.equipo.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no tiene un cliente con arriendo asociado')
        self.assertEqual(SolicitudHorometro.objects.count(), 1)

    # --- La página: dos celdas plegables -------------------------------------

    def test_la_pagina_trae_las_dos_celdas(self):
        """La bandeja y el historial de lecturas viven en la misma página."""
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, 'data-plegable="bandeja"')
        self.assertContains(response, 'data-plegable="lecturas"')
        self.assertContains(response, 'Bandeja de solicitudes')
        self.assertContains(response, 'Lecturas de horómetros')

    def test_las_celdas_nacen_cerradas(self):
        """Al entrar se ve el índice, no las tablas completas."""
        response = self.client.get(reverse('horometros:index'))
        self.assertEqual(response.content.decode().count('<details'), 2)
        self.assertNotContains(response, '<details open')

    def test_el_historial_vive_en_la_misma_pagina(self):
        self._lectura(valor='150.0')
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, '<th>Validada</th>')
        self.assertContains(response, '150,0')

    def test_el_historial_ya_no_es_una_pagina(self):
        """Dejó de ser una ruta suelta: no queda un camino paralelo a la misma tabla."""
        self.assertEqual(self.client.get('/horometros/lecturas/').status_code, 404)

    # --- Bandeja -------------------------------------------------------------

    def test_bandeja_muestra_la_fuente(self):
        SolicitudHorometro.objects.create(
            equipo=self.equipo, cliente=None, usuario_solicita=self.usuario,
            fuente='TELEMETRIA', fecha_solicitud=timezone.now(),
        )
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, '<th>Fuente</th>')
        self.assertContains(response, 'Telemetría')

    def test_bandeja_ofrece_las_dos_acciones_de_una_pendiente(self):
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, self.url_lectura())
        self.assertContains(response, self.url_borrar())

    def test_bandeja_lleva_los_datos_que_el_dialogo_necesita(self):
        """El botón trae el encabezado del diálogo: abrirlo no consulta al servidor."""
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, f'data-lectura="{self.url_lectura()}"')
        self.assertContains(response, 'data-equipo="EQ-001"')
        self.assertContains(response, 'data-fuente="cliente"')
        self.assertContains(response, 'data-cliente="Cliente X"')
        self.assertContains(response, 'data-actual="100,0"')

    def test_bandeja_muestra_una_pendiente_antigua(self):
        """El reloj no borra lo que todavía tiene un paso pendiente."""
        SolicitudHorometro.objects.filter(pk=self.solicitud.pk).update(
            fecha_solicitud=timezone.now() - timedelta(days=90)
        )
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, self.url_lectura())

    def test_bandeja_muestra_lo_resuelto_dentro_de_la_ventana(self):
        """Ya no hay nada que hacer, pero el cierre del día se alcanza a ver."""
        self.solicitud.cumplir(self._lectura())
        response = self.client.get(reverse('horometros:index'))
        self.assertContains(response, '>Cumplida<')
        self.assertNotContains(response, self.url_borrar())

    def test_bandeja_oculta_lo_resuelto_fuera_de_la_ventana(self):
        self.solicitud.cumplir(self._lectura())
        SolicitudHorometro.objects.filter(pk=self.solicitud.pk).update(
            fecha_resolucion=timezone.now() - timedelta(days=30)
        )
        response = self.client.get(reverse('horometros:index'))
        self.assertNotContains(response, '>Cumplida<')

    def test_bandeja_no_deduplica_por_equipo(self):
        """Dos pendientes de la misma máquina son dos obligaciones distintas."""
        SolicitudHorometro.objects.create(
            equipo=self.equipo, cliente=self.cliente, usuario_solicita=self.usuario,
            fuente='CLIENTE', fecha_solicitud=timezone.now(),
        )
        response = self.client.get(reverse('horometros:index'))
        self.assertEqual(response.content.decode().count('data-equipo="EQ-001"'), 2)

    # --- Registrar lectura: cerrar la solicitud ------------------------------

    def _lectura(self, valor='150.0'):
        return LecturaHorometro.objects.create(
            equipo=self.equipo, usuario=self.usuario, valor=Decimal(valor),
            fecha_hora=timezone.now(), fuente=LecturaHorometro.Fuente.CLIENTE,
            validada=True,
        )

    def test_registrar_lectura_cierra_la_solicitud(self):
        response = self.client.post(self.url_lectura(), {
            'valor': '150.0',
            'observacion': 'Reportado por el cliente',
        })
        self.assertRedirects(response, reverse('horometros:index'))
        self.solicitud.refresh_from_db()
        self.equipo.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudHorometro.Estado.CUMPLIDA)
        self.assertIsNotNone(self.solicitud.fecha_resolucion)
        self.assertEqual(self.solicitud.lectura.valor, Decimal('150.0'))
        self.assertEqual(self.solicitud.lectura.equipo, self.equipo)
        self.assertTrue(self.solicitud.lectura.validada)
        self.assertEqual(self.equipo.horometro_actual, Decimal('150.0'))

    def test_la_lectura_hereda_la_fuente_de_la_solicitud(self):
        """Al técnico se le pide el dato y el dato queda con esa fuente."""
        self.equipo.cambiarEstado(Equipo.Estado.DISPONIBLE)
        self.solicitud.fuente = 'TECNICO'
        self.solicitud.cliente = None
        self.solicitud.save(update_fields=['fuente', 'cliente'])

        self.client.post(self.url_lectura(), {'valor': '150.0', 'observacion': ''})

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.lectura.fuente, 'TECNICO')

    def test_registrar_lectura_rechaza_retroceso(self):
        response = self.client.post(self.url_lectura(), {
            'valor': '90.0',
            'observacion': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no puede ser menor')
        self.solicitud.refresh_from_db()
        self.assertTrue(self.solicitud.estaPendiente())
        self.assertEqual(LecturaHorometro.objects.count(), 0)

    def test_un_post_rechazado_reabre_el_dialogo(self):
        """El error tiene que quedar a la vista, no perderse detrás de la tabla."""
        response = self.client.post(self.url_lectura(), {'valor': '90.0', 'observacion': ''})
        self.assertContains(response, 'data-abrir-al-cargar="si"')
        self.assertContains(response, 'no puede ser menor')

    def test_registrar_lectura_abre_el_dialogo_en_la_bandeja(self):
        """No hay página aparte: el diálogo se abre sobre la bandeja."""
        response = self.client.get(self.url_lectura())
        self.assertContains(response, 'id="dialogo-lectura"')
        self.assertContains(response, 'data-abrir-al-cargar="si"')
        self.assertContains(response, f'action="{self.url_lectura()}"')
        self.assertContains(response, 'Horómetro del equipo EQ-001')
        self.assertContains(response, ', a Cliente X')

    def test_registrar_lectura_ignora_una_solicitud_ya_cerrada(self):
        self.solicitud.cumplir(self._lectura())
        response = self.client.post(self.url_lectura(), {'valor': '150.0', 'observacion': ''})
        self.assertRedirects(response, reverse('horometros:index'))
        self.assertEqual(LecturaHorometro.objects.count(), 1)

    # --- Borrar --------------------------------------------------------------

    def test_borrar_solicitud(self):
        response = self.client.post(self.url_borrar())
        self.assertRedirects(response, reverse('horometros:index'))
        self.assertFalse(SolicitudHorometro.objects.filter(pk=self.solicitud.pk).exists())

    def test_borrar_solo_acepta_post(self):
        response = self.client.get(self.url_borrar())
        self.assertEqual(response.status_code, 405)
        self.assertTrue(SolicitudHorometro.objects.filter(pk=self.solicitud.pk).exists())

    def test_borrar_no_toca_una_solicitud_ya_cerrada(self):
        """La lectura ya recibida es un dato real: no se borra con la solicitud."""
        self.solicitud.cumplir(self._lectura())
        self.client.post(self.url_borrar())
        self.assertTrue(SolicitudHorometro.objects.filter(pk=self.solicitud.pk).exists())
        self.assertEqual(LecturaHorometro.objects.count(), 1)

    # --- Arrendatario del equipo, para la celda del cliente ------------------

    def test_arrendatario_del_equipo_responde_el_cliente(self):
        response = self.client.get(
            reverse('horometros:arrendatario_del_equipo', args=[self.equipo.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'cliente': 'Cliente X'})

    def test_arrendatario_del_equipo_sin_arriendo_avisa(self):
        self.arriendo.delete()
        response = self.client.get(
            reverse('horometros:arrendatario_del_equipo', args=[self.equipo.id])
        )
        self.assertIsNone(response.json()['cliente'])
        self.assertIn('no tiene un cliente con arriendo asociado', response.json()['mensaje'])


class LimiteDeLecturasTest(TestCase):
    """El historial de la bandeja muestra solo las últimas lecturas, para no crecer sin límite."""

    def test_pagina_muestra_a_lo_mas_100_lecturas(self):
        from datetime import timedelta
        from django.urls import reverse
        from django.utils import timezone
        from cuentas.models import Rol, Usuario
        from flota.models import Equipo, TipoEquipo
        from horometros.models import LecturaHorometro
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        u = Usuario.objects.create_user(email='p@v.cl', password='test1234', nombre='P')
        e = Equipo.objects.create(tipo_equipo=TipoEquipo.objects.create(nombre='G', unidad_medida='HORAS'), codigo='Z1')
        ahora = timezone.now()
        LecturaHorometro.objects.bulk_create([
            LecturaHorometro(equipo=e, usuario=u, valor=i, fecha_hora=ahora - timedelta(days=150 - i), fuente='CLIENTE')
            for i in range(1, 131)])
        self.client.force_login(u)
        r = self.client.get(reverse('horometros:index'))
        self.assertEqual(len(r.context['lecturas']), 100)


class FuenteInternoTest(TestCase):
    """Un equipo en uso interno lo reporta quien lo tiene, no un cliente."""

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        self.interno = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-INT', estado=Equipo.Estado.INTERNO
        )

    def test_la_fuente_interno_ofrece_solo_equipos_internos(self):
        form = SolicitudHorometroForm(initial={'fuente': 'INTERNO'})
        self.assertEqual(list(form.fields['equipo'].queryset), [self.interno])

    def test_la_ficha_sugiere_interno(self):
        self.assertEqual(fuenteSugerida(self.interno), 'INTERNO')
