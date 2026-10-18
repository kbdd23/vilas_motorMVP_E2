from django.contrib import admin

from .models import Arriendo


@admin.register(Arriendo)
class ArriendoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'cliente', 'fecha_inicio', 'fecha_termino')
    list_filter = ('cliente',)
