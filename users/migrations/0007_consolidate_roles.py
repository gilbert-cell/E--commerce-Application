from django.db import migrations, models


def migrate_auditor_to_security(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(role='auditor').update(role='security')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_face_verified_at'),
    ]

    operations = [
        migrations.RunPython(migrate_auditor_to_security, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('customer', 'Customer'),
                    ('manager', 'Store Manager'),
                    ('security', 'Security Officer'),
                    ('admin', 'Administrator'),
                ],
                default='customer',
            ),
        ),
    ]
