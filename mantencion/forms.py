from django import forms

from horometros.services import ValidadorDatos

from .models import OrdenTrabajo, OrdenTrabajoInsumo, PlanMantencion, ServicioPlan


class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = ['equipo', 'servicio_plan', 'tipo', 'fecha_programada', 'observaciones']
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        datos = super().clean()
        equipo = datos.get('equipo')
        servicio = datos.get('servicio_plan')
        # Integridad de negocio: el servicio debe pertenecer al plan del tipo de equipo.
        if equipo and servicio and servicio.plan.tipo_equipo_id != equipo.tipo_equipo_id:
            self.add_error(
                'servicio_plan',
                f'El servicio «{servicio}» pertenece al plan de otro tipo de equipo; '
                f'elige un servicio del plan de {equipo.tipo_equipo}.',
            )
        return datos


class OrdenTrabajoInsumoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajoInsumo
        fields = ['insumo', 'cantidad_usada', 'notas']


class CerrarOrdenForm(forms.Form):
    """Cierra una OT con el horómetro que reportó el técnico.

    El equipo llega por el constructor porque la regla no depende solo del dato:
    el horómetro no retrocede, y contra qué compararlo lo sabe el equipo, no el
    formulario.
    """

    horometro_cierre = forms.DecimalField(
        label='Horómetro de cierre',
        max_digits=10,
        decimal_places=1,
    )

    def __init__(self, *args, equipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipo = equipo

    def clean_horometro_cierre(self):
        valor = self.cleaned_data['horometro_cierre']
        if self.equipo is not None and not ValidadorDatos().validar(self.equipo, valor):
            raise forms.ValidationError(
                'El horómetro de cierre no puede ser menor al horómetro actual del equipo.'
            )
        return valor


class PlanMantencionForm(forms.ModelForm):
    class Meta:
        model = PlanMantencion
        fields = ['tipo_equipo', 'nombre']


class ServicioPlanForm(forms.ModelForm):
    class Meta:
        model = ServicioPlan
        fields = ['plan', 'nombre', 'intervalo_horas', 'descripcion']
