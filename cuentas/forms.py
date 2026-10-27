from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import Cliente, Usuario


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['rut', 'razon_social', 'email_contacto', 'telefono', 'activo']


class RegistroForm(forms.Form):
    """Alta de cuenta con email y contraseña, nada más.

    El modelo exige un nombre, que se deriva del email; el rol lo pone el manager
    (planificador, el único que existe hoy).
    """

    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password, user=Usuario(email=self.cleaned_data.get('email', '')))
        return password

    def save(self):
        email = self.cleaned_data['email']
        nombre = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        return Usuario.objects.create_user(
            email=email,
            password=self.cleaned_data['password'],
            nombre=nombre,
        )
