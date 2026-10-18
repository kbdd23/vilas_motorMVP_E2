from django.contrib import admin

from .models import Equipo, TipoEquipo


@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad_medida')
    search_fields = ('nombre',)


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo_equipo', 'patente', 'marca', 'modelo', 'estado', 'horometro_actual')
    list_filter = ('estado', 'tipo_equipo')
    search_fields = ('codigo', 'patente', 'numero_serie')
