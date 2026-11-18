from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.cache import cache
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from .models import Cliente, Usuario


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput)

    error_bloqueo = (
        'Demasiados intentos fallidos con este correo. '
        'Espera unos minutos antes de volver a intentarlo.'
    )

    @staticmethod
    def clave_intentos(email):
        return f'login_fallos:{(email or "").strip().lower()}'

    @property
    def bloqueado(self):
        return self.has_error(NON_FIELD_ERRORS, 'bloqueado')

    def clean(self):
        """Bloquea el correo tras varios fallos seguidos (protección contra fuerza bruta)."""
        clave = self.clave_intentos(self.data.get('username'))
        fallos = cache.get(clave, 0)
        if fallos >= settings.LOGIN_MAX_INTENTOS:
            raise ValidationError(self.error_bloqueo, code='bloqueado')
        try:
            datos = super().clean()
        except ValidationError:
            cache.set(clave, fallos + 1, timeout=settings.LOGIN_BLOQUEO_SEGUNDOS)
            raise
        cache.delete(clave)
        return datos


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['rut', 'razon_social', 'email_contacto', 'telefono', 'activo']


class UsuarioForm(UserCreationForm):
    """Alta de usuarios desde el sistema, con contraseñas hasheadas por Django."""

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ['nombre', 'email', 'rol', 'cliente', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'nombre': forms.TextInput(attrs={'autocomplete': 'name'}),
        }


class VerificacionForm(forms.Form):
    """Código de seis caracteres que llega al correo de la cuenta."""

    codigo = forms.CharField(
        label='Código',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'one-time-code'}),
    )

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()
