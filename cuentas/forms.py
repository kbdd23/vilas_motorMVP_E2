from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Cliente, Usuario


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput)


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
