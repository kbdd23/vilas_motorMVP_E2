from django.urls import path

from . import views

app_name = 'horometros'

urlpatterns = [
    path('horometros/', views.index, name='index'),
    path('horometros/solicitudes/nueva/', views.crear_solicitud, name='crear_solicitud'),
    path('horometros/solicitudes/<int:pk>/lectura/', views.registrar_lectura, name='registrar_lectura'),
    path('horometros/solicitudes/<int:pk>/borrar/', views.borrar_solicitud, name='borrar_solicitud'),
    path('horometros/equipos/<int:pk>/arrendatario/', views.arrendatario_del_equipo, name='arrendatario_del_equipo'),
]
