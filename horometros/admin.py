from django.contrib import admin

from .models import LecturaHorometro, SolicitudHorometro


@admin.register(LecturaHorometro)
class LecturaHorometroAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'valor', 'fecha_hora', 'fuente', 'validada')
    list_filter = ('fuente', 'validada')
    search_fields = ('equipo__codigo',)


@admin.register(SolicitudHorometro)
class SolicitudHorometroAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'cliente', 'fecha_solicitud', 'estado')
    list_filter = ('estado',)
