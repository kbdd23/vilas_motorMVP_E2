from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import LoginForm

app_name = 'cuentas'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('mantenciones-pendientes/', views.mantenimientos_pendientes, name='mantenimientos_pendientes'),
    path('mantenciones-vencidas/', views.mantenimientos_vencidos, name='mantenimientos_vencidos'),
    path('mantenciones-por-vencer/', views.mantenimientos_por_vencer, name='mantenimientos_por_vencer'),
    path('catalogos/', views.catalogos, name='catalogos'),
    path('clientes/', views.lista_clientes, name='clientes'),
    path('clientes/nueva/', views.crear_cliente, name='crear_cliente'),
    path('usuarios/', views.lista_usuarios, name='usuarios'),
    path('usuarios/nuevo/', views.crear_usuario, name='crear_usuario'),
    path('login/', auth_views.LoginView.as_view(
        template_name='cuentas/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('recuperar-acceso/', auth_views.PasswordResetView.as_view(
        template_name='cuentas/password_reset_form.html',
        email_template_name='cuentas/password_reset_email.txt',
        subject_template_name='cuentas/password_reset_subject.txt',
        success_url=reverse_lazy('cuentas:password_reset_done'),
    ), name='password_reset'),
    path('recuperar-acceso/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='cuentas/password_reset_done.html',
    ), name='password_reset_done'),
    path('restablecer/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='cuentas/password_reset_confirm.html',
        success_url=reverse_lazy('cuentas:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('restablecer/completo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='cuentas/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('verificar/', views.verificar, name='verificar'),
    path('verificar/reenviar/', views.reenviar_codigo, name='reenviar_codigo'),
    path('diagnostico/', views.diagnostico, name='diagnostico'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
