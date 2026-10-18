from django.contrib import admin

from .models import ArchivoAdjunto, Auditoria


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'entidad', 'id_registro', 'operacion', 'usuario', 'ip')
    list_filter = ('operacion', 'entidad')

    # La auditoría es de solo lectura: nadie puede agregar, editar ni borrar eventos desde el panel.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArchivoAdjunto)
class ArchivoAdjuntoAdmin(admin.ModelAdmin):
    list_display = ('nombre_original', 'entidad', 'id_registro', 'mime', 'subido_en')
