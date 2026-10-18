from django.db import migrations, models


def backfill_fecha_resolucion(apps, schema_editor):
    """Rellena la fecha de resolución de las solicitudes ya resueltas.

    Las anteriores a este cambio no la guardaban, así que sin esto quedarían
    fuera de la bandeja para siempre. Se usa la fecha de la lectura para las
    cumplidas y la de la solicitud para las vencidas, que es el mejor dato
    disponible.
    """
    SolicitudHorometro = apps.get_model('horometros', 'SolicitudHorometro')
    for solicitud in SolicitudHorometro.objects.exclude(estado='PENDIENTE'):
        if solicitud.lectura_id:
            solicitud.fecha_resolucion = solicitud.lectura.fecha_hora
        else:
            solicitud.fecha_resolucion = solicitud.fecha_solicitud
        solicitud.save(update_fields=['fecha_resolucion'])


class Migration(migrations.Migration):

    dependencies = [
        ('horometros', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudhorometro',
            name='fecha_resolucion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_fecha_resolucion, migrations.RunPython.noop),
    ]
