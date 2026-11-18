from django.db import migrations, models


class Migration(migrations.Migration):
    """Índices para las consultas frecuentes del dashboard y las bandejas."""

    dependencies = [
        ('horometros', '0005_alter_lecturahorometro_fuente_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='lecturahorometro',
            index=models.Index(fields=['equipo', '-fecha_hora'], name='idx_lectura_equipo_fecha'),
        ),
        migrations.AddIndex(
            model_name='solicitudhorometro',
            index=models.Index(fields=['estado'], name='idx_solicitud_estado'),
        ),
    ]
