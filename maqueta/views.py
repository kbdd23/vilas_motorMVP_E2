from django.db.models import Count
from django.http import JsonResponse
from django.views.generic import TemplateView

from flota.models import Equipo


class MaquetaView(TemplateView):
    """Sirve la maqueta de Rodrigo como una vista más del sistema."""

    template_name = "maqueta/maqueta.html"


def flota_geojson(request):
    """Flota real como GeoJSON para el mapa de Leaflet.

    Se omiten los equipos sin coordenadas: el mapa solo dibuja lo que tiene
    ubicación, nunca inventa pines.
    """
    features = []
    for equipo in Equipo.objects.select_related("tipo_equipo"):
        if equipo.latitud is None or equipo.longitud is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(equipo.longitud), float(equipo.latitud)],
                },
                "properties": {
                    "codigo": equipo.codigo,
                    "marca": equipo.marca or "",
                    "modelo": equipo.modelo or "",
                    "estado": equipo.estado,
                    "horometro": float(equipo.horometro_actual),
                    "tipo": equipo.tipo_equipo.nombre,
                    "unidad": equipo.tipo_equipo.unidad_medida,
                    "ubicacion": equipo.ubicacion or "",
                },
            }
        )
    return JsonResponse({"type": "FeatureCollection", "features": features})


def dashboard(request):
    """Resumen agregado para las tarjetas del dashboard de la maqueta."""
    por_estado = {
        fila["estado"]: fila["total"]
        for fila in Equipo.objects.values("estado").annotate(total=Count("id"))
    }
    por_tipo = {
        fila["tipo_equipo__nombre"]: fila["total"]
        for fila in Equipo.objects.values("tipo_equipo__nombre").annotate(
            total=Count("id")
        )
    }
    return JsonResponse(
        {
            "total_equipos": Equipo.objects.count(),
            "georreferenciados": Equipo.objects.exclude(latitud__isnull=True).exclude(
                longitud__isnull=True
            ).count(),
            "por_estado": por_estado,
            "por_tipo": por_tipo,
        }
    )
