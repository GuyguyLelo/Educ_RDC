from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0015_personnel_reference_acte_engagement'),
    ]

    operations = [
        migrations.AddField(
            model_name='personnelecole',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='personnels/photos/',
                verbose_name='Photo',
            ),
        ),
    ]
