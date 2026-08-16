from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0007_credential_biometrique'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='connexion_biometrique',
            field=models.BooleanField(
                default=False,
                help_text='Permet à l’utilisateur d’enregistrer et d’utiliser l’empreinte / Face ID / Windows Hello.',
                verbose_name='Connexion biométrique autorisée',
            ),
        ),
    ]
