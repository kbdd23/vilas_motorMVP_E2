from django.db import migrations, models


class Migration(migrations.Migration):
    """Índices para las consultas frecuentes del dashboard y las bandejas."""

    dependencies = [
        ('flota', '0005_equipo_ubicacion'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['estado'], name='idx_equipo_estado'),
        ),
    ]
