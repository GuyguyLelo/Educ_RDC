import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0008_section_option_classe'),
        ('evaluations', '0002_verrouillage_periode'),
    ]

    operations = [
        migrations.AddField(
            model_name='matiere',
            name='section',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='matieres',
                to='ecoles.sectionscolaire',
                verbose_name='Section',
            ),
        ),
        migrations.AddField(
            model_name='matiere',
            name='option',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='matieres',
                to='ecoles.optionscolaire',
                verbose_name='Option',
            ),
        ),
        migrations.AddField(
            model_name='matiere',
            name='classe',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='matieres_catalogue',
                to='ecoles.classe',
                verbose_name='Classe',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='matiere',
            name='uniq_matiere_nom_ecole',
        ),
        migrations.AddConstraint(
            model_name='matiere',
            constraint=models.UniqueConstraint(
                fields=('ecole', 'nom', 'section', 'option', 'classe'),
                name='uniq_matiere_scope_ecole',
            ),
        ),
    ]
