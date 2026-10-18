from django.db import migrations, models
import django.db.models.deletion


def copiar_fuente_desde_la_lectura(apps, schema_editor):
    """Da fuente a las solicitudes que ya existían.

    La fuente no se guardaba. Las que tienen lectura vinculada la heredan de ella
    (que es la regla nueva) y el resto eran pedidos al cliente, que era la única
    fuente que existía.
    """
    SolicitudHorometro = apps.get_model('horometros', 'SolicitudHorometro')
    for solicitud in SolicitudHorometro.objects.all():
        solicitud.fuente = solicitud.lectura.fuente if solicitud.lectura_id else 'CLIENTE'
        solicitud.save(update_fields=['fuente'])


def convertir_vencidas_en_pendientes(apps, schema_editor):
    """Las vencidas vuelven a la bandeja como pendientes.

    El estado VENCIDA desaparece: una solicitud se cierra ingresando el dato que
    se recibió o se borra. Las que quedaron marcadas como vencidas nunca
    recibieron su dato, así que vuelven a ser una obligación viva en vez de
    desaparecer en silencio.
    """
    SolicitudHorometro = apps.get_model('horometros', 'SolicitudHorometro')
    SolicitudHorometro.objects.filter(estado='VENCIDA').update(
        estado='PENDIENTE', fecha_resolucion=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ('horometros', '0002_solicitudhorometro_fecha_resolucion'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudhorometro',
            name='fuente',
            field=models.CharField(choices=[('CLIENTE', 'Cliente'), ('TECNICO', 'Técnico'), ('TELEMETRIA', 'Telemetría')], default='CLIENTE', max_length=15),
            preserve_default=False,
        ),
        migrations.RunPython(copiar_fuente_desde_la_lectura, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='solicitudhorometro',
            name='cliente',
            field=models.ForeignKey(blank=True, db_column='id_cliente', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='solicitudes_horometro', to='cuentas.cliente'),
        ),
        migrations.RunPython(convertir_vencidas_en_pendientes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='solicitudhorometro',
            name='estado',
            field=models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('CUMPLIDA', 'Cumplida')], default='PENDIENTE', max_length=10),
        ),
    ]
