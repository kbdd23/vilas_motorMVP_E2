from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = 'cuentas'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('catalogos/', views.catalogos, name='catalogos'),
    path('clientes/', views.lista_clientes, name='clientes'),
    path('clientes/nueva/', views.crear_cliente, name='crear_cliente'),
    path('login/', auth_views.LoginView.as_view(
        template_name='cuentas/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
