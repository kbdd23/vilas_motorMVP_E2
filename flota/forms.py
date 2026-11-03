import re

from django import forms
from django.db import models

from .models import Equipo, TipoEquipo


class TipoEquipoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipo
        fields = ['nombre', 'unidad_medida']


class EquipoForm(forms.ModelForm):
    class ModoCodigo(models.TextChoices):
        AUTOMATICO = 'AUTO', 'Generar automáticamente'
        MANUAL = 'MANUAL', 'Ingresar manualmente'

    modo_codigo = forms.ChoiceField(
        choices=ModoCodigo.choices,
        initial=ModoCodigo.AUTOMATICO,
        required=False,
        widget=forms.RadioSelect,
        label='Código del equipo',
        help_text='El código automático usa el tipo de equipo y un correlativo, por ejemplo GEN-001.',
    )

    class Meta:
        model = Equipo
        fields = ['codigo', 'tipo_equipo', 'patente', 'marca', 'modelo', 'numero_serie', 'estado', 'horometro_actual']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Al editar, el código ya asignado no se cambia: es la identidad del equipo.
            del self.fields['modo_codigo']
            del self.fields['codigo']
            return
        self.fields['codigo'].required = False
        self.fields['codigo'].help_text = 'Solo es obligatorio si eliges ingreso manual.'

    @staticmethod
    def codigo_automatico(tipo_equipo):
        """Devuelve el siguiente código disponible para un tipo de equipo."""
        base = re.sub(r'[^A-Z0-9]+', '', tipo_equipo.nombre.upper())[:8] or 'EQ'
        correlativo = 1
        while Equipo.objects.filter(codigo=f'{base}-{correlativo:03d}').exists():
            correlativo += 1
        return f'{base}-{correlativo:03d}'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk:
            return cleaned_data
        # El modo ausente mantiene compatibilidad con integraciones/formularios
        # anteriores: si enviaban un código se considera manual.
        modo = cleaned_data.get('modo_codigo') or (
            self.ModoCodigo.MANUAL if cleaned_data.get('codigo') else self.ModoCodigo.AUTOMATICO
        )
        tipo_equipo = cleaned_data.get('tipo_equipo')
        codigo = (cleaned_data.get('codigo') or '').strip().upper()

        if modo == self.ModoCodigo.AUTOMATICO and tipo_equipo:
            cleaned_data['codigo'] = self.codigo_automatico(tipo_equipo)
        elif modo == self.ModoCodigo.MANUAL:
            if not codigo:
                self.add_error('codigo', 'Ingresa el código que deseas asignar.')
            else:
                cleaned_data['codigo'] = codigo
        return cleaned_data
