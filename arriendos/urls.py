from django.urls import path

from . import views

app_name = 'arriendos'

urlpatterns = [
    path('arriendos/', views.lista_arriendos, name='arriendos'),
    path('arriendos/nuevo/', views.crear_arriendo, name='crear_arriendo'),
    path('arriendos/<int:pk>/cerrar/', views.cerrar_arriendo, name='cerrar_arriendo'),
]
