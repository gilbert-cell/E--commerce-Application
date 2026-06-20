from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                max_length=20,
                choices=[('credit_card', 'Credit Card')],
                default='credit_card',
            ),
        ),
    ]
