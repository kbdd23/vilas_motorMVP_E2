from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario

from .forms import InsumoForm
from .models import Insumo


class InsumoTest(TestCase):
    """Catálogo de insumos: alta, validaciones y acceso."""

    def setUp(self):
        Rol.objects.get_or_create(nombre='planificador', defaults={'descripcion': 'Planificador'})
        self.usuario = Usuario.objects.create_user(
            email='plan@vilas.cl', password='test1234', nombre='Planificador'
        )
        self.client.force_login(self.usuario)

    def test_lista_muestra_insumos_ordenados_por_nombre(self):
        Insumo.objects.create(codigo='FIL-01', nombre='Filtro de aire')
        Insumo.objects.create(codigo='ACE-01', nombre='Aceite 15W40')
        response = self.client.get(reverse('insumos:insumos'))
        self.assertEqual(response.status_code, 200)
        nombres = [i.nombre for i in response.context['insumos']]
        self.assertEqual(nombres, ['Aceite 15W40', 'Filtro de aire'])

    def test_crear_insumo_valido_redirige_a_la_lista(self):
        response = self.client.post(reverse('insumos:crear_insumo'), {
            'codigo': 'REF-01', 'nombre': 'Refrigerante', 'unidad_medida': 'litro',
        })
        self.assertRedirects(response, reverse('insumos:insumos'))
        self.assertTrue(Insumo.objects.filter(codigo='REF-01').exists())

    def test_unidad_de_medida_es_opcional(self):
        form = InsumoForm(data={'codigo': 'GRA-01', 'nombre': 'Grasa', 'unidad_medida': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_codigo_y_nombre_son_obligatorios(self):
        form = InsumoForm(data={'codigo': '', 'nombre': '', 'unidad_medida': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('codigo', form.errors)
        self.assertIn('nombre', form.errors)

    def test_codigo_duplicado_se_rechaza_en_el_formulario(self):
        Insumo.objects.create(codigo='FIL-01', nombre='Filtro de aire')
        response = self.client.post(reverse('insumos:crear_insumo'), {
            'codigo': 'FIL-01', 'nombre': 'Otro filtro', 'unidad_medida': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Insumo.objects.filter(codigo='FIL-01').count(), 1)

    def test_codigo_duplicado_se_rechaza_en_la_base(self):
        Insumo.objects.create(codigo='FIL-01', nombre='Filtro de aire')
        with self.assertRaises(IntegrityError):
            Insumo.objects.create(codigo='FIL-01', nombre='Duplicado')

    def test_codigo_supera_largo_maximo(self):
        form = InsumoForm(data={'codigo': 'X' * 31, 'nombre': 'Largo', 'unidad_medida': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('codigo', form.errors)

    def test_sin_sesion_redirige_al_login(self):
        self.client.logout()
        response = self.client.get(reverse('insumos:insumos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('cuentas:login'), response['Location'])
