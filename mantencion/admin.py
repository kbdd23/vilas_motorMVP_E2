from django.contrib import admin

from .models import (
    OrdenTrabajo,
    OrdenTrabajoInsumo,
    PlanMantencion,
    ServicioPlan,
    ServicioPlanInsumo,
)


@admin.register(PlanMantencion)
class PlanMantencionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_equipo')
    search_fields = ('nombre',)


@admin.register(ServicioPlan)
class ServicioPlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'plan', 'intervalo_horas')
    list_filter = ('plan',)


@admin.register(ServicioPlanInsumo)
class ServicioPlanInsumoAdmin(admin.ModelAdmin):
    list_display = ('servicio_plan', 'insumo', 'cantidad')


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('numero_ot', 'equipo', 'tipo', 'estado', 'fecha_programada', 'fecha_ejecucion')
    list_filter = ('estado', 'tipo')
    search_fields = ('numero_ot',)


@admin.register(OrdenTrabajoInsumo)
class OrdenTrabajoInsumoAdmin(admin.ModelAdmin):
    list_display = ('orden_trabajo', 'insumo', 'cantidad_usada', 'notas')
