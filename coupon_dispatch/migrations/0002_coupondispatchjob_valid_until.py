from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon_dispatch', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupondispatchjob',
            name='valid_until',
            field=models.DateField(blank=True, null=True, verbose_name='Действует до'),
        ),
    ]
