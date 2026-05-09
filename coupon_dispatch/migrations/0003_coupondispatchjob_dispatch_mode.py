from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon_dispatch', '0002_coupondispatchjob_valid_until'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupondispatchjob',
            name='dispatch_mode',
            field=models.CharField(
                choices=[
                    ('marketing_sale', 'По маркетинговой акции'),
                    ('predefined_coupon', 'Готовые коды из Excel'),
                ],
                default='marketing_sale',
                max_length=32,
                verbose_name='Режим рассылки',
            ),
        ),
    ]
