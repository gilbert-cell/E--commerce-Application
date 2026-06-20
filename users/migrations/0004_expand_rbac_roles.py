from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_last_login_ip_user_last_login_timestamp_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('customer', 'Customer'),
                    ('admin', 'Administrator'),
                    ('security', 'Security Officer'),
                    ('manager', 'Product Manager'),
                    ('auditor', 'System Auditor'),
                ],
                default='customer',
                max_length=20,
            ),
        ),
    ]
