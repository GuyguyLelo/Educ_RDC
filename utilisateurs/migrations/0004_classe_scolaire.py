import django.db.models.deletion
from django.db import migrations, models


def migrer_classes_utilisateurs(apps, schema_editor):
    Utilisateur = apps.get_model('utilisateurs', 'Utilisateur')
    Classe = apps.get_model('ecoles', 'Classe')
    for user in Utilisateur.objects.exclude(classe_nom_legacy='').exclude(classe_nom_legacy__isnull=True).iterator():
        nom = (user.classe_nom_legacy or '').strip()
        if not nom or not user.ecole_id:
            continue
        obj, _ = Classe.objects.get_or_create(
            ecole_id=user.ecole_id,
            nom=nom,
            defaults={'active': True},
        )
        user.classe_id = obj.id
        user.save(update_fields=['classe_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ecoles', '0007_classe_scolaire'),
        ('eleves', '0003_classe_scolaire'),
        ('utilisateurs', '0003_utilisateur_classe_titulaire'),
    ]

    operations = [
        migrations.RenameField(
            model_name='utilisateur',
            old_name='classe',
            new_name='classe_nom_legacy',
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='classe',
            field=models.ForeignKey(
                blank=True,
                help_text="Classe dont l'enseignant est titulaire — limite l'accès aux élèves de cette classe.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='enseignants',
                to='ecoles.classe',
                verbose_name='Classe (titulaire)',
            ),
        ),
        migrations.RunPython(migrer_classes_utilisateurs, noop_reverse),
        migrations.RemoveField(
            model_name='utilisateur',
            name='classe_nom_legacy',
        ),
    ]
