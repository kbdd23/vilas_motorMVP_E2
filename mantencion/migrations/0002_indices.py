from django.db import migrations, models


class Migration(migrations.Migration):
    """Índices para las consultas frecuentes del dashboard y las bandejas."""

    dependencies = [
        ('mantencion', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='ordentrabajo',
            index=models.Index(fields=['estado'], name='idx_ot_estado'),
        ),
        migrations.AddIndex(
            model_name='ordentrabajo',
            index=models.Index(fields=['equipo', 'estado'], name='idx_ot_equipo_estado'),
        ),
    ]
