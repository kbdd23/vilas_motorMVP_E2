from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cuentas.urls')),
    path('', include('flota.urls')),
    path('', include('insumos.urls')),
    path('', include('horometros.urls')),
    path('', include('arriendos.urls')),
    path('', include('mantencion.urls')),
]

# En desarrollo, Django sirve los archivos de media/ directamente.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
