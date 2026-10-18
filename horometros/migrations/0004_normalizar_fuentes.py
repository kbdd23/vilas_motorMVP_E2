from django.db import migrations

# Las únicas fuentes a las que se le puede pedir un horómetro.
FUENTES_VALIDAS = ['CLIENTE', 'TECNICO', 'TELEMETRIA']


def normalizar_fuentes(apps, schema_editor):
    """Deja las solicitudes con una fuente a la que se le pueda pedir.

    La migración anterior copió la fuente de la lectura vinculada, y una lectura
    sí puede venir de planificación, que no es una fuente a la que se le pida
    nada. Esas solicitudes quedan como pedidos al cliente, que es lo que eran.
    """
    SolicitudHorometro = apps.get_model('horometros', 'SolicitudHorometro')
    SolicitudHorometro.objects.exclude(fuente__in=FUENTES_VALIDAS).update(fuente='CLIENTE')


class Migration(migrations.Migration):

    dependencies = [
        ('horometros', '0003_solicitudhorometro_fuente'),
    ]

    operations = [
        migrations.RunPython(normalizar_fuentes, migrations.RunPython.noop),
    ]
