from datetime import date
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from arriendos.models import Arriendo
from cuentas.models import Cliente, Rol, Usuario
from flota.models import Equipo, TipoEquipo
from horometros.models import LecturaHorometro
from mantencion.models import OrdenTrabajo


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

    def test_crear_equipo_con_codigo_automatico(self):
        Equipo.objects.create(tipo_equipo=self.tipo, codigo='GENERADO-001')
        response = self.client.post(reverse('flota:crear_equipo'), {
            'modo_codigo': 'AUTO',
            'tipo_equipo': self.tipo.id,
            'patente': '',
            'marca': '',
            'modelo': '',
            'numero_serie': '',
            'estado': Equipo.Estado.DISPONIBLE,
            'horometro_actual': '0.0',
        })
        self.assertRedirects(response, reverse('flota:equipos'))
        self.assertTrue(Equipo.objects.filter(codigo='GENERADO-002').exists())

    def test_codigo_manual_es_normalizado(self):
        response = self.client.post(reverse('flota:crear_equipo'), {
            'modo_codigo': 'MANUAL',
            'codigo': ' mi-eq-14 ',
            'tipo_equipo': self.tipo.id,
            'patente': '',
            'marca': '',
            'modelo': '',
            'numero_serie': '',
            'estado': Equipo.Estado.DISPONIBLE,
            'horometro_actual': '0.0',
        })
        self.assertRedirects(response, reverse('flota:equipos'))
        self.assertTrue(Equipo.objects.filter(codigo='MI-EQ-14').exists())

    def test_editar_equipo_no_cambia_el_codigo(self):
        equipo = Equipo.objects.create(tipo_equipo=self.tipo, codigo='MI-EQ-99')
        response = self.client.post(reverse('flota:editar_equipo', args=[equipo.pk]), {
            'tipo_equipo': self.tipo.id,
            'patente': '',
            'marca': 'JCB',
            'modelo': '',
            'numero_serie': '',
            'estado': Equipo.Estado.DISPONIBLE,
            'horometro_actual': '0.0',
        })
        self.assertRedirects(response, reverse('flota:detalle_equipo', args=[equipo.pk]))
        equipo.refresh_from_db()
        self.assertEqual(equipo.codigo, 'MI-EQ-99')
        self.assertEqual(equipo.marca, 'JCB')


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


class PosicionesFlotaTest(TestCase):
    """El mapa en vivo solo recibe equipos que reportaron posición."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador del sistema de gestión de mantenimiento'})
        self.usuario = Usuario.objects.create_user(email='mapa@vilas.cl', password='test1234', nombre='Mapa')
        self.client.force_login(self.usuario)
        self.tipo = TipoEquipo.objects.create(
            nombre='Grúa horquilla', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.ubicado = Equipo.objects.create(
            tipo_equipo=self.tipo,
            codigo='EQ-001',
            latitud=Decimal('-20.220800'),
            longitud=Decimal('-70.141400'),
            ultima_senal=timezone.now(),
        )
        self.sin_senal = Equipo.objects.create(tipo_equipo=self.tipo, codigo='EQ-002')

    def test_solo_devuelve_equipos_con_ubicacion(self):
        respuesta = self.client.get(reverse('flota:posiciones'))
        datos = respuesta.json()

        self.assertEqual([posicion['codigo'] for posicion in datos['posiciones']], ['EQ-001'])
        self.assertEqual(datos['total'], 1)
        self.assertEqual(datos['sin_ubicacion'], 1)
        self.assertAlmostEqual(datos['posiciones'][0]['lat'], -20.2208, places=4)
        self.assertAlmostEqual(datos['posiciones'][0]['lng'], -70.1414, places=4)

    def test_la_posicion_trae_el_enlace_a_la_ficha(self):
        respuesta = self.client.get(reverse('flota:posiciones'))
        posicion = respuesta.json()['posiciones'][0]

        self.assertEqual(posicion['url'], reverse('flota:detalle_equipo', args=[self.ubicado.id]))
        self.assertEqual(posicion['estado'], Equipo.Estado.DISPONIBLE)

    def test_la_posicion_trae_los_datos_del_panel_lateral(self):
        Equipo.objects.filter(pk=self.ubicado.pk).update(
            patente='ABCD12', horometro_actual=Decimal('123.4')
        )
        posicion = self.client.get(reverse('flota:posiciones')).json()['posiciones'][0]

        self.assertEqual(posicion['patente'], 'ABCD12')
        self.assertEqual(posicion['horometro'], '123.4')
        self.assertEqual(posicion['tipo'], 'Grúa horquilla')

    def test_sin_coordenadas_el_mapa_recibe_lista_vacia(self):
        Equipo.objects.filter(pk=self.ubicado.pk).update(latitud=None, longitud=None)
        datos = self.client.get(reverse('flota:posiciones')).json()

        self.assertEqual(datos['posiciones'], [])
        self.assertEqual(datos['total'], 0)
        self.assertEqual(datos['sin_ubicacion'], 2)


class ExportacionFlotaTest(TestCase):
    """Las planillas de flota respetan el filtro y traen los datos reales."""

    def setUp(self):
        self.rol, _ = Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='excel@vilas.cl', password='test1234', nombre='Excel')
        self.client.force_login(self.usuario)
        self.tipo = TipoEquipo.objects.create(
            nombre='Grúa horquilla', unidad_medida=TipoEquipo.UnidadMedida.HORAS
        )
        self.disponible = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-001',
            estado=Equipo.Estado.DISPONIBLE, horometro_actual=Decimal('10.5'),
        )
        self.en_faena = Equipo.objects.create(
            tipo_equipo=self.tipo, codigo='EQ-002', estado=Equipo.Estado.EN_FAENA,
        )

    def _hoja(self, respuesta):
        return load_workbook(BytesIO(respuesta.content)).active

    def test_exportar_flota_devuelve_un_xlsx(self):
        respuesta = self.client.get(reverse('flota:exportar_flota'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('spreadsheetml', respuesta['Content-Type'])
        self.assertIn('attachment', respuesta['Content-Disposition'])

        hoja = self._hoja(respuesta)
        self.assertEqual(hoja['A1'].value, 'Código')
        self.assertEqual(hoja.max_row, 3)

    def test_exportar_flota_con_ultima_senal_no_falla(self):
        """La última señal llega con zona horaria y openpyxl la rechaza si no se convierte."""
        Equipo.objects.filter(pk=self.disponible.pk).update(ultima_senal=timezone.now())
        respuesta = self.client.get(reverse('flota:exportar_flota'))

        self.assertEqual(respuesta.status_code, 200)
        hoja = self._hoja(respuesta)
        self.assertIsNotNone(hoja['I2'].value)

    def test_exportar_flota_respeta_el_filtro(self):
        respuesta = self.client.get(reverse('flota:exportar_flota'), {'estado': 'EN_FAENA'})
        hoja = self._hoja(respuesta)

        self.assertEqual(hoja.max_row, 2)
        self.assertEqual(hoja['A2'].value, 'EQ-002')

    def test_exportar_historial_usa_el_formato_del_taller(self):
        OrdenTrabajo.objects.create(
            equipo=self.disponible, tipo='PREVENTIVA', numero_ot='89867',
            fecha_ejecucion=date(2023, 10, 16), horometro_cierre=Decimal('828.0'),
        )
        respuesta = self.client.get(
            reverse('flota:exportar_historial', args=[self.disponible.id])
        )
        hoja = self._hoja(respuesta)

        self.assertEqual(hoja['A4'].value, 'N° DE EQUIPO: EQ-001')
        self.assertEqual(hoja['B11'].value, '89867')
        self.assertEqual(hoja['D11'].value, 'Preventiva')

    def _entrar_con_rol(self, nombre_rol):
        """Cambia la sesión a un usuario con otro rol."""
        rol, _ = Rol.objects.get_or_create(nombre=nombre_rol, defaults={'descripcion': nombre_rol})
        usuario = Usuario.objects.create_user(
            email=f'{nombre_rol}@vilas.cl', password='test1234', nombre=nombre_rol
        )
        usuario.rol = rol
        usuario.email_verificado = True
        usuario.save(update_fields=['rol', 'email_verificado'])
        self.client.force_login(usuario)

    def test_otro_rol_no_puede_exportar(self):
        self._entrar_con_rol('operador')

        self.assertEqual(self.client.get(reverse('flota:exportar_flota')).status_code, 403)
        self.assertEqual(
            self.client.get(
                reverse('flota:exportar_historial', args=[self.disponible.id])
            ).status_code,
            403,
        )

    def test_el_administrador_tambien_puede_exportar(self):
        self._entrar_con_rol('administrador')

        respuesta = self.client.get(reverse('flota:exportar_flota'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('spreadsheetml', respuesta['Content-Type'])

    def test_el_boton_solo_aparece_para_planificador(self):
        self._entrar_con_rol('operador')
        self.assertNotContains(
            self.client.get(reverse('flota:equipos')),
            reverse('flota:exportar_flota'),
        )

        self.client.force_login(self.usuario)
        self.assertContains(
            self.client.get(reverse('flota:equipos')),
            reverse('flota:exportar_flota'),
        )


class CargarFlotaTest(TestCase):
    """Carga masiva de la flota desde la planilla Equipos.xlsx (prueba de volumen)."""

    def _planilla(self, filas):
        import os
        import tempfile

        from openpyxl import Workbook

        libro = Workbook()
        hoja = libro.active
        hoja.append(['MAQUINARIA', 'FABRICANTE', 'MODELO', 'N° INTERNO', 'PPU'])
        for fila in filas:
            hoja.append(fila)
        archivo = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        archivo.close()
        libro.save(archivo.name)
        self.addCleanup(os.remove, archivo.name)
        return archivo.name

    def _cargar(self, ruta):
        from io import StringIO

        from django.core.management import call_command

        call_command('cargar_flota', archivo=ruta, stdout=StringIO())

    def test_clasifica_tipo_unidad_y_capacidad(self):
        from flota.carga_flota import clasificar

        self.assertEqual(clasificar('GRUA HORQUILLA 03 TON GAS'), ('Grúa horquilla', 'HORAS', 'GH', '3 TON GAS'))
        self.assertEqual(clasificar('GENERADOR 45 KVA'), ('Generador', 'HORAS', 'GEN', '45 KVA'))
        self.assertEqual(clasificar('CAMIONETA')[:3], ('Camioneta', 'KM', 'CTA'))
        self.assertEqual(clasificar('CAMION PLUMA')[0], 'Camión pluma')
        self.assertEqual(clasificar('FURGÓN')[0], 'Furgón')

    def test_maquinaria_desconocida_avisa(self):
        from django.core.management.base import CommandError

        ruta = self._planilla([['NAVE ESPACIAL', 'X', 'Y', None, None]])
        with self.assertRaises(CommandError):
            self._cargar(ruta)

    def test_carga_equipos_con_codigo_por_tipo(self):
        ruta = self._planilla([
            ['GRUA HORQUILLA 7 TON', 'KOMATSU', 'FD70-10', None, None],
            ['GRUA HORQUILLA 3 TON', 'KOMATSU', 'FD30T17', None, None],
            ['CAMIONETA', 'TOYOTA', 'HILUX', None, None],
        ])
        self._cargar(ruta)
        self.assertEqual(Equipo.objects.count(), 3)
        grua = Equipo.objects.get(codigo='GH-001')
        self.assertEqual(grua.modelo, 'FD70-10 (7 TON)')
        self.assertEqual(grua.tipo_equipo.unidad_medida, TipoEquipo.UnidadMedida.HORAS)
        self.assertEqual(Equipo.objects.get(codigo='CTA-001').tipo_equipo.unidad_medida, TipoEquipo.UnidadMedida.KM)

    def test_ejecutarla_dos_veces_no_duplica(self):
        ruta = self._planilla([['COMPRESOR', 'ATLAS COPCO', 'XAS 97', None, None]])
        self._cargar(ruta)
        equipo = Equipo.objects.get(codigo='COM-001')
        equipo.actualizarHorometro(Decimal('1200.0'))
        self._cargar(ruta)
        self.assertEqual(Equipo.objects.count(), 1)
        self.assertEqual(Equipo.objects.get(codigo='COM-001').horometro_actual, Decimal('1200.0'))

    def test_reutiliza_el_tipo_existente(self):
        TipoEquipo.objects.create(nombre='Generador', unidad_medida=TipoEquipo.UnidadMedida.HORAS)
        ruta = self._planilla([['GENERADOR 45 KVA', 'JCB', 'G45QX', None, None]])
        self._cargar(ruta)
        self.assertEqual(TipoEquipo.objects.filter(nombre='Generador').count(), 1)

    def test_volumen_de_400_equipos(self):
        filas = [['LUMINARIA', 'PRAMAC', f'T.LED {i}', None, None] for i in range(400)]
        self._cargar(self._planilla(filas))
        self.assertEqual(Equipo.objects.filter(codigo__startswith='LUM-').count(), 400)
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        usuario = Usuario.objects.create_user(email='vol@vilas.cl', password='test1234', nombre='Volumen')
        self.client.force_login(usuario)
        respuesta_lista = self.client.get(reverse('flota:equipos'))
        self.assertEqual(respuesta_lista.status_code, 200)
        self.assertContains(respuesta_lista, 'LUM-400')
