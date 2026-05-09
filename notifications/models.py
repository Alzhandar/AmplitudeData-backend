from django.db import models

from notifications.choices import NotificationType


class NotificationSchedule(models.Model):
	notification_type = models.CharField(max_length=32, choices=NotificationType.choices, unique=True, verbose_name='Тип уведомления')
	send_time = models.TimeField(verbose_name='Время отправки (Asia/Almaty)')
	queue_create_time = models.TimeField(null=True, blank=True, verbose_name='Время создания очереди (Asia/Almaty)')
	enabled = models.BooleanField(default=True, verbose_name='Включено')
	last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name='Последняя проверка очереди')
	last_queue_entry_created_at = models.DateTimeField(null=True, blank=True, verbose_name='Последнее создание записи очереди')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		ordering = ('notification_type',)
		verbose_name = 'Расписание уведомления'
		verbose_name_plural = 'Расписания уведомлений'

	def __str__(self) -> str:
		return f'{self.notification_type} @ {self.send_time}'


class NotificationTemplate(models.Model):
	notification_type = models.CharField(max_length=32, choices=NotificationType.choices, unique=True, verbose_name='Тип уведомления')
	title = models.CharField(max_length=255, verbose_name='Заголовок (RU)')
	body = models.TextField(verbose_name='Текст (RU)')
	title_kz = models.CharField(max_length=255, blank=True, verbose_name='Заголовок (KZ)')
	body_kz = models.TextField(blank=True, verbose_name='Текст (KZ)')
	city = models.CharField(max_length=128, blank=True, verbose_name='Город (опционально)')
	park = models.CharField(max_length=128, blank=True, verbose_name='Парк (опционально)')
	notification_backend_type = models.CharField(max_length=64, default='default', verbose_name='notification_type для mobile API')
	survey_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='survey_id (опционально)')
	review_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='review_id (опционально)')
	enabled = models.BooleanField(default=True, verbose_name='Включен')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		ordering = ('notification_type',)
		verbose_name = 'Шаблон push-уведомления'
		verbose_name_plural = 'Шаблоны push-уведомлений'

	def __str__(self) -> str:
		return f'{self.notification_type}: {self.title}'


class StoryRecipientConfig(models.Model):
	notification_type = models.CharField(max_length=32, choices=NotificationType.choices, unique=True, verbose_name='Тип уведомления')
	story_id = models.PositiveBigIntegerField(db_index=True, verbose_name='ID готового Story во внешнем API')
	story_date = models.DateField(null=True, blank=True, db_index=True, verbose_name='Дата Story (Asia/Almaty)')
	enabled = models.BooleanField(default=True, verbose_name='Включен')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		ordering = ('notification_type',)
		verbose_name = 'Настройка Story получателя'
		verbose_name_plural = 'Настройки Story получателей'

	def __str__(self) -> str:
		return f'{self.notification_type}: story_id={self.story_id}'


class KidBirthdayNotification(models.Model):
	notification_type = models.CharField(max_length=32, choices=NotificationType.choices, verbose_name='Тип уведомления')
	birthday_date = models.DateField(db_index=True, verbose_name='Дата дня рождения')
	kid_id = models.PositiveBigIntegerField(db_index=True, verbose_name='ID ребенка')
	kid_name = models.CharField(max_length=255, blank=True, verbose_name='Имя ребенка')
	guest_id = models.PositiveBigIntegerField(db_index=True, verbose_name='ID гостя')
	guest_phone = models.CharField(max_length=64, blank=True, verbose_name='Телефон гостя')
	schedule_date = models.DateField(db_index=True, verbose_name='Дата отправки')
	scheduled_for = models.DateTimeField(db_index=True, verbose_name='Запланировано на')
	sent = models.BooleanField(default=False, db_index=True, verbose_name='Уведомление отправлено')
	sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Время отправки')
	processing_started_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Взято в обработку')
	story_created = models.BooleanField(default=False, verbose_name='Story создан')
	external_story_id = models.PositiveBigIntegerField(null=True, blank=True, verbose_name='ID Story во внешнем API')
	last_error = models.TextField(blank=True, verbose_name='Последняя ошибка')
	kid_payload = models.JSONField(default=dict, blank=True, verbose_name='Raw payload kid')
	guest_payload = models.JSONField(default=dict, blank=True, verbose_name='Raw payload guest')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('notification_type', 'schedule_date', 'kid_id'),
				name='uniq_kid_birthday_notification_once_per_day',
			),
		]
		ordering = ('sent', 'scheduled_for', 'id')
		verbose_name = 'Очередь уведомления о ДР ребенка'
		verbose_name_plural = 'Очередь уведомлений о ДР детей'

	def __str__(self) -> str:
		return f'{self.kid_id} / {self.schedule_date} / sent={self.sent}'


class PushDispatchStatus(models.TextChoices):
	ACCEPTED = 'accepted', 'Accepted'
	FAILED = 'failed', 'Failed'


class PushDispatchLog(models.Model):
	initiated_by = models.ForeignKey(
		'auth.User',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='push_dispatch_logs',
		verbose_name='Initiator',
	)
	initiated_by_email = models.EmailField(blank=True, verbose_name='Initiator email')
	target = models.CharField(max_length=16, verbose_name='Target')
	city_id = models.PositiveBigIntegerField(null=True, blank=True, verbose_name='City ID')
	recipients_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='Recipients count')
	title = models.CharField(max_length=255, blank=True, verbose_name='Title (RU)')
	body = models.TextField(blank=True, verbose_name='Body (RU)')
	title_kz = models.CharField(max_length=255, blank=True, verbose_name='Title (KZ)')
	body_kz = models.TextField(blank=True, verbose_name='Body (KZ)')
	notification_type = models.CharField(max_length=64, default='default', verbose_name='Notification type')
	survey_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='Survey ID')
	review_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='Review ID')
	notification_id = models.PositiveBigIntegerField(null=True, blank=True, verbose_name='External notification ID')
	status = models.CharField(
		max_length=16,
		choices=PushDispatchStatus.choices,
		default=PushDispatchStatus.ACCEPTED,
		db_index=True,
		verbose_name='Status',
	)
	error_message = models.TextField(blank=True, verbose_name='Error message')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

	class Meta:
		ordering = ('-created_at',)
		verbose_name = 'Push dispatch log'
		verbose_name_plural = 'Push dispatch logs'

	def __str__(self) -> str:
		return f'#{self.id} {self.target} {self.status}'
