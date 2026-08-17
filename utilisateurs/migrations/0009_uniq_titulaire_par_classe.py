from django.db import migrations, models


def dedupe_titulaires(apps, schema_editor):
    Utilisateur = apps.get_model('utilisateurs', 'Utilisateur')
    vus = set()
    qs = Utilisateur.objects.filter(
        role='enseignant', classe_id__isnull=False,
    ).order_by('id')
    for user in qs.iterator():
        cid = user.classe_id
        if cid in vus:
            user.classe_id = None
            user.save(update_fields=['classe_id'])
        else:
            vus.add(cid)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0008_utilisateur_connexion_biometrique'),
    ]

    operations = [
        migrations.RunPython(dedupe_titulaires, noop_reverse),
        migrations.AddConstraint(
            model_name='utilisateur',
            constraint=models.UniqueConstraint(
                condition=models.Q(('classe__isnull', False), ('role', 'enseignant')),
                fields=('classe',),
                name='uniq_enseignant_titulaire_par_classe',
            ),
        ),
    ]
