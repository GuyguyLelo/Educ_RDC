from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0005_eleve_qr_code_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='numero_impot',
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                unique=True,
                verbose_name='Numéro Impôt',
            ),
        ),
    ]
