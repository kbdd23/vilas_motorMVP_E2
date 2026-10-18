from django.urls import path

from . import views

app_name = 'insumos'

urlpatterns = [
    path('insumos/', views.lista_insumos, name='insumos'),
    path('insumos/nueva/', views.crear_insumo, name='crear_insumo'),
]
