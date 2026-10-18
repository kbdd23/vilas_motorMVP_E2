from django.urls import path

from . import views

app_name = 'flota'

urlpatterns = [
    path('equipos/', views.lista_equipos, name='equipos'),
    path('equipos/nueva/', views.crear_equipo, name='crear_equipo'),
    path('equipos/<int:pk>/', views.detalle_equipo, name='detalle_equipo'),
    path('equipos/<int:pk>/disponible/', views.marcar_disponible, name='marcar_disponible'),
    path('equipos/<int:pk>/estado/', views.cambiar_estado, name='cambiar_estado'),
    path('tipos-equipo/', views.lista_tipos_equipo, name='tipos_equipo'),
    path('tipos-equipo/nueva/', views.crear_tipo_equipo, name='crear_tipo_equipo'),
]
