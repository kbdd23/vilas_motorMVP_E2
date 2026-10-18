from django import forms

from .models import Equipo, TipoEquipo


class TipoEquipoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipo
        fields = ['nombre', 'unidad_medida']


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['codigo', 'tipo_equipo', 'patente', 'marca', 'modelo', 'numero_serie', 'estado', 'horometro_actual']
