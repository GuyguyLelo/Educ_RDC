from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0007_classe_scolaire'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('evaluations', '0001_initial_evaluation_notes_bulletins'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerrouillagePeriode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_verrouillage', models.DateTimeField(auto_now_add=True, verbose_name='Date de verrouillage')),
                ('annee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='verrouillages_periodes',
                    to='evaluations.anneescolaire',
                    verbose_name='Année scolaire',
                )),
                ('classe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='verrouillages_periodes',
                    to='ecoles.classe',
                    verbose_name='Classe',
                )),
                ('periode', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='verrouillages',
                    to='evaluations.periodeevaluation',
                    verbose_name='Période',
                )),
                ('verrouille_par', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='periodes_verrouillees',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Verrouillé par',
                )),
            ],
            options={
                'verbose_name': 'Verrouillage de période',
                'verbose_name_plural': 'Verrouillages de périodes',
            },
        ),
        migrations.AddConstraint(
            model_name='verrouillageperiode',
            constraint=models.UniqueConstraint(
                fields=('annee', 'classe', 'periode'),
                name='uniq_verrou_periode_classe',
            ),
        ),
    ]
