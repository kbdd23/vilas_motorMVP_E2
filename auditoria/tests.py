from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from auditoria.models import Auditoria
from cuentas.models import Cliente, Rol, Usuario


class AuditoriaAutomaticaTest(TestCase):
    """Cada INSERT/UPDATE/DELETE hecho por un usuario autenticado queda registrado."""

    def setUp(self):
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Plan')
        self.client.force_login(self.usuario)

    def test_insert_por_vista_queda_auditado(self):
        self.client.post(reverse('cuentas:crear_cliente'), {
            'rut': '76123456-7', 'razon_social': 'Minera Sur', 'email_contacto': 'a@b.cl',
            'telefono': '123', 'activo': 'on',
        })
        cliente = Cliente.objects.get(rut='76123456-7')
        fila = Auditoria.objects.get(entidad='cliente', id_registro=cliente.pk)
        self.assertEqual(fila.operacion, 'INSERT')
        self.assertEqual(fila.usuario, self.usuario)
        self.assertIsNone(fila.valor_anterior)
        self.assertEqual(fila.valor_nuevo['razon_social'], 'Minera Sur')
        self.assertEqual(fila.ip, '127.0.0.1')

    def test_update_guarda_valor_anterior_y_nuevo(self):
        cliente = Cliente.objects.create(rut='1-9', razon_social='Antes')
        Auditoria.objects.all().delete()
        # Simula el contexto de una petición autenticada
        from auditoria.middleware import _contexto
        token = _contexto.set((self.usuario, '10.0.0.5'))
        try:
            cliente.razon_social = 'Despues'
            cliente.save()
        finally:
            _contexto.reset(token)
        fila = Auditoria.objects.get(entidad='cliente', operacion='UPDATE')
        self.assertEqual(fila.valor_anterior['razon_social'], 'Antes')
        self.assertEqual(fila.valor_nuevo['razon_social'], 'Despues')
        self.assertEqual(fila.ip, '10.0.0.5')

    def test_delete_queda_auditado(self):
        cliente = Cliente.objects.create(rut='2-7', razon_social='Borrar')
        from auditoria.middleware import _contexto
        token = _contexto.set((self.usuario, None))
        try:
            pk = cliente.pk
            cliente.delete()
        finally:
            _contexto.reset(token)
        fila = Auditoria.objects.get(entidad='cliente', id_registro=pk, operacion='DELETE')
        self.assertEqual(fila.valor_anterior['rut'], '2-7')
        self.assertIsNone(fila.valor_nuevo)

    def test_sin_usuario_no_se_audita(self):
        Cliente.objects.create(rut='3-5', razon_social='Carga de datos')
        self.assertFalse(Auditoria.objects.filter(entidad='cliente').exists())

    def test_nunca_se_guarda_la_contrasena(self):
        from auditoria.middleware import _contexto
        token = _contexto.set((self.usuario, None))
        try:
            self.usuario.nombre = 'Otro nombre'
            self.usuario.save()
        finally:
            _contexto.reset(token)
        fila = Auditoria.objects.filter(entidad='usuario', operacion='UPDATE').latest('id')
        self.assertNotIn('password', fila.valor_anterior)
        self.assertNotIn('password', fila.valor_nuevo)


class SeguridadConfiguracionTest(TestCase):
    """Estándares de codificación segura que dependen de la configuración."""

    def test_contrasena_minimo_12_caracteres(self):
        with self.assertRaises(ValidationError):
            validate_password('Corta1234')
        validate_password('Una-clave-larga-y-poco-comun-2026')

    def test_cabeceras_de_seguridad(self):
        respuesta = self.client.get(reverse('cuentas:login'))
        self.assertEqual(respuesta.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(respuesta.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(respuesta.headers['Referrer-Policy'], 'same-origin')

    def test_cookie_de_sesion_no_accesible_desde_js(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')

    def test_vistas_exigen_login(self):
        respuesta = self.client.get(reverse('cuentas:dashboard'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/login/', respuesta.url)


class AdaptabilidadTest(TestCase):
    """La hoja de estilos define puntos de quiebre para pantallas pequeñas."""

    def test_css_tiene_media_queries(self):
        css = (Path(settings.BASE_DIR) / 'static' / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('@media (max-width: 768px)', css)
        self.assertIn('@media (max-width: 900px)', css)

    def test_plantilla_base_declara_viewport(self):
        respuesta = self.client.get(reverse('cuentas:login'))
        self.assertContains(respuesta, 'name="viewport"')


class SeedDemoTest(TestCase):
    """Defecto hallado al ejecutar el MVP: seed_demo fallaba por un estado inexistente (VENCIDA)."""

    def test_seed_demo_carga_sin_errores(self):
        from django.core.management import call_command
        from io import StringIO
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        Usuario.objects.create_user(email='plan@vilas.cl', password='test1234', nombre='Plan')
        salida = StringIO()
        call_command('seed_demo', stdout=salida)
        self.assertIn('Datos de demostración cargados', salida.getvalue())


class AuditoriaSoloLecturaTest(TestCase):
    """El registro de auditoría no se puede alterar desde el panel de administración."""

    def test_admin_no_permite_agregar_editar_ni_borrar(self):
        from django.contrib import admin
        from django.test import RequestFactory
        modelo_admin = admin.site._registry[Auditoria]
        peticion = RequestFactory().get('/')
        self.assertFalse(modelo_admin.has_add_permission(peticion))
        self.assertFalse(modelo_admin.has_change_permission(peticion))
        self.assertFalse(modelo_admin.has_delete_permission(peticion))
