from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Cliente, Rol, Usuario


class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('email', 'nombre', 'rol', 'cliente')


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = '__all__'


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Admin de Usuario: login por email, con manejo seguro del password."""

    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    ordering = ('email',)
    list_display = ('email', 'nombre', 'rol', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'rol')
    search_fields = ('email', 'nombre')
    readonly_fields = ('last_login', 'creado_en')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre', 'rol', 'cliente')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'creado_en')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'rol', 'cliente', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'razon_social', 'email_contacto', 'telefono', 'activo')
    search_fields = ('rut', 'razon_social')
    list_filter = ('activo',)
