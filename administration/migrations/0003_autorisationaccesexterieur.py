import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutorisationAccesExterieur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adresse_ip', models.GenericIPAddressField(verbose_name='Adresse IP')),
                ('geo_label', models.CharField(blank=True, max_length=255, verbose_name='Localisation')),
                ('country_code', models.CharField(blank=True, max_length=8, verbose_name='Code pays')),
                ('statut', models.CharField(
                    choices=[
                        ('en_attente', 'En attente'),
                        ('autorise', 'Autorisé'),
                        ('refuse', 'Refusé'),
                        ('revoque', 'Révoqué'),
                    ],
                    default='en_attente',
                    max_length=20,
                    verbose_name='Statut',
                )),
                ('date_demande', models.DateTimeField(auto_now_add=True, verbose_name='Date de demande')),
                ('date_decision', models.DateTimeField(blank=True, null=True, verbose_name='Date de décision')),
                ('date_expiration', models.DateTimeField(blank=True, null=True, verbose_name='Expiration')),
                ('motif', models.CharField(blank=True, max_length=255, verbose_name='Motif / commentaire')),
                ('decide_par', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='decisions_acces_exterieur',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Décidé par',
                )),
                ('utilisateur', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='autorisations_acces_exterieur',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Utilisateur',
                )),
            ],
            options={
                'verbose_name': 'Autorisation accès extérieur',
                'verbose_name_plural': 'Autorisations accès extérieur',
                'ordering': ['-date_demande'],
            },
        ),
        migrations.AddIndex(
            model_name='autorisationaccesexterieur',
            index=models.Index(fields=['statut', 'utilisateur'], name='administrat_statut_6c0d0d_idx'),
        ),
    ]
