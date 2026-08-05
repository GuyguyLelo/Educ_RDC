import django.db.models.deletion
from django.db import migrations, models


def migrer_classes_eleves(apps, schema_editor):
    Eleve = apps.get_model('eleves', 'Eleve')
    Classe = apps.get_model('ecoles', 'Classe')
    cache = {}
    for eleve in Eleve.objects.exclude(classe_nom_legacy='').exclude(classe_nom_legacy__isnull=True).iterator():
        nom = (eleve.classe_nom_legacy or '').strip()
        if not nom or not eleve.ecole_id:
            continue
        key = (eleve.ecole_id, nom.lower())
        if key not in cache:
            obj, _ = Classe.objects.get_or_create(
                ecole_id=eleve.ecole_id,
                nom=nom,
                defaults={'active': True},
            )
            cache[key] = obj.id
        eleve.classe_id = cache[key]
        eleve.save(update_fields=['classe_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0007_classe_scolaire'),
        ('eleves', '0002_eleve_numero_identification_permanent'),
    ]

    operations = [
        migrations.RenameField(
            model_name='eleve',
            old_name='classe',
            new_name='classe_nom_legacy',
        ),
        migrations.AddField(
            model_name='eleve',
            name='classe',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='eleves',
                to='ecoles.classe',
                verbose_name='Classe',
            ),
        ),
        migrations.RunPython(migrer_classes_eleves, noop_reverse),
        migrations.RemoveField(
            model_name='eleve',
            name='classe_nom_legacy',
        ),
    ]
