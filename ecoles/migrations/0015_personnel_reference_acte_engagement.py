from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0014_personnel_utilisateur_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='personnelecole',
            name='reference_acte_engagement',
            field=models.CharField(
                blank=True,
                help_text="N° / référence de l'acte d'engagement de l'agent.",
                max_length=80,
                verbose_name="Référence de l'acte d'engagement",
            ),
        ),
    ]
