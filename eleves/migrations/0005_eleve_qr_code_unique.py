import uuid

from django.db import migrations, models


def _default_code():
    return f'ELV-{uuid.uuid4().hex[:16].upper()}'


def populate_codes(apps, schema_editor):
    Eleve = apps.get_model('eleves', 'Eleve')
    for eleve in Eleve.objects.all().iterator():
        if not eleve.code_unique:
            eleve.code_unique = _default_code()
            eleve.save(update_fields=['code_unique'])


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0004_parents_identite_photos_contacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='code_unique',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Identifiant stable encodé dans le QR code de l’élève.',
                max_length=40,
                verbose_name='Code unique QR',
            ),
        ),
        migrations.AddField(
            model_name='eleve',
            name='qr_code',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='eleves/qr/',
                verbose_name='QR Code',
            ),
        ),
        migrations.RunPython(populate_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='eleve',
            name='code_unique',
            field=models.CharField(
                default=_default_code,
                editable=False,
                help_text='Identifiant stable encodé dans le QR code de l’élève.',
                max_length=40,
                unique=True,
                verbose_name='Code unique QR',
            ),
        ),
    ]
