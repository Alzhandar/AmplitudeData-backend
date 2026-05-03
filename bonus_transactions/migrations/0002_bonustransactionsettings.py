from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bonus_transactions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonusTransactionSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('singleton_guard', models.BooleanField(default=True, editable=False, unique=True)),
                ('base_id_prefix', models.CharField(default='bonus', max_length=255, verbose_name='Префикс base_id по умолчанию')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Настройки начисления бонусов',
                'verbose_name_plural': 'Настройки начисления бонусов',
            },
        ),
    ]
