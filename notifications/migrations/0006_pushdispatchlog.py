from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_storyrecipientconfig_story_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PushDispatchLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('initiated_by_email', models.EmailField(blank=True, max_length=254, verbose_name='Initiator email')),
                ('target', models.CharField(max_length=16, verbose_name='Target')),
                ('city_id', models.PositiveBigIntegerField(blank=True, null=True, verbose_name='City ID')),
                ('recipients_count', models.PositiveIntegerField(blank=True, null=True, verbose_name='Recipients count')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Title (RU)')),
                ('body', models.TextField(blank=True, verbose_name='Body (RU)')),
                ('title_kz', models.CharField(blank=True, max_length=255, verbose_name='Title (KZ)')),
                ('body_kz', models.TextField(blank=True, verbose_name='Body (KZ)')),
                ('notification_type', models.CharField(default='default', max_length=64, verbose_name='Notification type')),
                ('survey_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='Survey ID')),
                ('review_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='Review ID')),
                ('notification_id', models.PositiveBigIntegerField(blank=True, null=True, verbose_name='External notification ID')),
                ('status', models.CharField(choices=[('accepted', 'Accepted'), ('failed', 'Failed')], db_index=True, default='accepted', max_length=16, verbose_name='Status')),
                ('error_message', models.TextField(blank=True, verbose_name='Error message')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('initiated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='push_dispatch_logs', to=settings.AUTH_USER_MODEL, verbose_name='Initiator')),
            ],
            options={
                'verbose_name': 'Push dispatch log',
                'verbose_name_plural': 'Push dispatch logs',
                'ordering': ('-created_at',),
            },
        ),
    ]
