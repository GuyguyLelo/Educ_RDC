from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0009_uniq_titulaire_par_classe'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='session_key_courante',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Clé de la session Django actuellement en ligne (une seule à la fois).',
                max_length=40,
                verbose_name='Session de connexion',
            ),
        ),
    ]
