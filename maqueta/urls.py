from django.urls import path

from . import views

urlpatterns = [
    path("maqueta/", views.MaquetaView.as_view(), name="maqueta"),
    path("api/flota/", views.flota_geojson, name="api_flota"),
    path("api/dashboard/", views.dashboard, name="api_dashboard"),
]
