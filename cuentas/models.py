from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UsuarioManager

class Rol(models.Model):
    """
    Roles de negocio. Hoy solo existe 'planificador'; la tabla queda para escalar a otros tipos de roles.
    """
    id = models.SmallAutoField(primary_key=True, db_column='id_rol')
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = 'rol'

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """Cliente(razón social) dueño o arrendatario de los equipos."""
    id = models.AutoField(primary_key=True, db_column='id_cliente')
    rut = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=120)
    email_contacto = models.EmailField(max_length=120, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cliente'

    def __str__(self):
        return self.razon_social

class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema. Login por email; los privilegos los da Django"""
    id = models.AutoField(primary_key=True, db_column='id_usuario')
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column='id_rol', related_name='usuarios')
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.PROTECT, db_column='id_cliente', related_name="usuarios")
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=120, unique=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_column='activo')
    last_login = models.DateTimeField(null=True, blank=True, db_column='ultimo_acceso')
    is_staff = models.BooleanField(default=False) # PermissionsMixin no lo treae: se declara explicitamente.

    password = models.CharField(max_length=255, db_column='password_hash')

    class Meta:
        db_table = 'usuario'

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    def __str__(self):
        return self.email
