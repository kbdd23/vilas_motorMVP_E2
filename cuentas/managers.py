"""Patrón Factory, crea usuarios y los gestiona."""
from django.contrib.auth.base_user import BaseUserManager

class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    ROL_PLANIFICADOR = 'planificador'
    ROL_CLIENTE = 'cliente'


    def _crear_usuario(self, email, password, rol, **campos_extra):
        if not email:
            raise ValueError('El email es obligatorio.')
        email = self.normalize_email(email)
        usuario = self.model(email=email, rol=rol, **campos_extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def _obtener_rol(self, nombre):
        from .models import Rol # import local: ahorra ciclos entre managers to models

        try:
            return Rol.objects.get(nombre=nombre)
        except Rol.DoesNotExist:
            raise ValueError(f"No existe el rol '{nombre}'.")


    def create_user(self, email, password=None, **campos_extra):
        for campo in ('rol', 'is_staff', 'is_superuser'):
            if campo in campos_extra:
                raise ValueError("create_user() no acepta inserción de campos.")
        campos_extra['is_staff'] = True
        campos_extra['is_superuser'] = False
        rol = self._obtener_rol(self.ROL_PLANIFICADOR) #Ahora solo es planificador por "default" porque no existen más roles en el sistema
        return self._crear_usuario(email, password, rol, **campos_extra)

    def create_superuser(self, email, password=None, **campos_extra):
        for campo in ('rol', 'is_staff', 'is_superuser'):
            if campo in campos_extra:
                raise ValueError("create_superuser() no acepta inserción de campos.")
        campos_extra['is_staff'] = True
        campos_extra['is_superuser'] = True
        campos_extra['is_active'] = True
        rol = self._obtener_rol(self.ROL_PLANIFICADOR)
        return self._crear_usuario(email, password, rol, **campos_extra)