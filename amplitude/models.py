from django.db import models


class MobileSession(models.Model):
    date = models.DateField(db_index=True, verbose_name='Дата')
    event_time = models.DateTimeField(db_index=True, verbose_name='Время события')
    event_type = models.CharField(max_length=255, blank=True, verbose_name='Тип события')
    user_id = models.CharField(max_length=255, blank=True, verbose_name='ID пользователя')
    device_id = models.CharField(max_length=255, db_index=True, verbose_name='ID устройства')
    phone_number = models.CharField(max_length=64, blank=True, verbose_name='Номер телефона')
    platform = models.CharField(max_length=64, blank=True, verbose_name='Платформа')
    device_brand = models.CharField(max_length=128, blank=True, verbose_name='Бренд устройства')
    device_manufacturer = models.CharField(max_length=128, blank=True, verbose_name='Производитель устройства')
    device_model = models.CharField(max_length=128, blank=True, verbose_name='Модель устройства')
    insert_id = models.CharField(max_length=255, blank=True, verbose_name='Insert ID')
    dedupe_key = models.CharField(max_length=64, unique=True, verbose_name='Ключ дедупликации')
    raw_event = models.JSONField(default=dict, blank=True, verbose_name='Сырое событие')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        ordering = ('-event_time',)
        verbose_name = 'Сессия мобильного события'
        verbose_name_plural = 'Сессии мобильных событий'


class DailyDeviceActivity(models.Model):
    date = models.DateField(db_index=True, verbose_name='Дата')
    user_id = models.CharField(max_length=255, blank=True, verbose_name='ID пользователя')
    device_id = models.CharField(max_length=255, db_index=True, verbose_name='ID устройства')
    phone_number = models.CharField(max_length=64, blank=True, verbose_name='Номер телефона')
    platform = models.CharField(max_length=64, blank=True, verbose_name='Платформа')
    device_brand = models.CharField(max_length=128, blank=True, verbose_name='Бренд устройства')
    device_manufacturer = models.CharField(max_length=128, blank=True, verbose_name='Производитель устройства')
    device_model = models.CharField(max_length=128, blank=True, verbose_name='Модель устройства')
    visits_count = models.PositiveIntegerField(default=0, verbose_name='Количество визитов')
    first_seen = models.DateTimeField(null=True, blank=True, verbose_name='Первый визит')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Последний визит')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('date', 'device_id'), name='uniq_daily_activity_per_device'),
        ]
        ordering = ('-last_seen',)
        verbose_name = 'Дневная активность устройства'
        verbose_name_plural = 'Дневная активность устройств'


class DeviceVisitTime(models.Model):
    daily_activity = models.ForeignKey(
        DailyDeviceActivity,
        on_delete=models.CASCADE,
        related_name='visit_records',
        verbose_name='Дневная активность',
    )
    event_time = models.DateTimeField(db_index=True, verbose_name='Время визита')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('daily_activity', 'event_time'), name='uniq_visit_time_per_activity'),
        ]
        ordering = ('event_time',)
        verbose_name = 'Время визита устройства'
        verbose_name_plural = 'Времена визитов устройств'


class AmplitudeSyncSchedule(models.Model):
    enabled = models.BooleanField(default=True, verbose_name='Включено')
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='Последний запуск (время)')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Amplitude Sync Schedule'
        verbose_name_plural = 'Amplitude Sync Schedules'

    def __str__(self) -> str:
        return f'Hourly sync (enabled={self.enabled})'
