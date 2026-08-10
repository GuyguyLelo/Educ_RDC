import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0007_classe_scolaire'),
    ]

    operations = [
        migrations.CreateModel(
            name='SectionScolaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=120, verbose_name='Nom')),
                ('code', models.CharField(blank=True, max_length=30, verbose_name='Code')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('ecole', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sections',
                    to='ecoles.ecole',
                    verbose_name='École',
                )),
            ],
            options={
                'verbose_name': 'Section scolaire',
                'verbose_name_plural': 'Sections scolaires',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='OptionScolaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=150, verbose_name='Nom')),
                ('code', models.CharField(blank=True, max_length=30, verbose_name='Code')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('section', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='options',
                    to='ecoles.sectionscolaire',
                    verbose_name='Section',
                )),
            ],
            options={
                'verbose_name': 'Option scolaire',
                'verbose_name_plural': 'Options scolaires',
                'ordering': ['section__nom', 'nom'],
            },
        ),
        migrations.AddField(
            model_name='classe',
            name='section',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='classes',
                to='ecoles.sectionscolaire',
                verbose_name='Section',
            ),
        ),
        migrations.AddField(
            model_name='classe',
            name='option',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='classes',
                to='ecoles.optionscolaire',
                verbose_name='Option',
            ),
        ),
        migrations.AddConstraint(
            model_name='sectionscolaire',
            constraint=models.UniqueConstraint(fields=('ecole', 'nom'), name='uniq_section_nom_ecole'),
        ),
        migrations.AddConstraint(
            model_name='optionscolaire',
            constraint=models.UniqueConstraint(fields=('section', 'nom'), name='uniq_option_nom_section'),
        ),
    ]
