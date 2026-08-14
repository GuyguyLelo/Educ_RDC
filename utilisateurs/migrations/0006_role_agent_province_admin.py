from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0005_utilisateur_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='utilisateur',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrateur'),
                    ('agent_national', 'Agent National'),
                    ('agent_province_admin', 'Agent Province administrative'),
                    ('agent_provincial', 'Agent Province éducationnelle'),
                    ('agent_antenne', 'Agent Antenne'),
                    ('admin_ecole', 'Administratif école'),
                    ('enseignant', 'Enseignant'),
                ],
                default='agent_antenne',
                max_length=30,
                verbose_name='Rôle',
            ),
        ),
    ]
