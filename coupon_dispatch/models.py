from django.db import models


class CouponDispatchJobStatus(models.TextChoices):
	PENDING = 'pending', 'Ожидает'
	PROCESSING = 'processing', 'В обработке'
	COMPLETED = 'completed', 'Завершено'
	FAILED = 'failed', 'Ошибка'


class CouponDispatchInputSource(models.TextChoices):
	MANUAL = 'manual', 'Ручной ввод'
	EXCEL = 'excel', 'Excel файл'
	MIXED = 'mixed', 'Смешанный'


class CouponDispatchMode(models.TextChoices):
	MARKETING_SALE = 'marketing_sale', 'По маркетинговой акции'
	PREDEFINED_COUPON = 'predefined_coupon', 'Готовые коды из Excel'


class CouponDispatchJob(models.Model):
	title = models.CharField(max_length=255, verbose_name='Название купона для приложения')
	dispatch_mode = models.CharField(
		max_length=32,
		choices=CouponDispatchMode.choices,
		default=CouponDispatchMode.MARKETING_SALE,
		verbose_name='Режим рассылки',
	)
	marketing_sale_id = models.PositiveBigIntegerField(db_index=True, verbose_name='ID маркетинговой акции')
	marketing_sale_name = models.CharField(max_length=255, blank=True, verbose_name='Название маркетинговой акции')
	valid_until = models.DateField(null=True, blank=True, verbose_name='Действует до')
	initiated_by = models.ForeignKey(
		'auth.User',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='coupon_dispatch_jobs',
		verbose_name='Инициатор',
	)
	input_source = models.CharField(
		max_length=16,
		choices=CouponDispatchInputSource.choices,
		default=CouponDispatchInputSource.MANUAL,
		verbose_name='Источник телефонов',
	)
	source_text = models.TextField(blank=True, verbose_name='Телефоны (ручной ввод)')
	source_file = models.FileField(upload_to='coupon_dispatch/', null=True, blank=True, verbose_name='Excel файл')
	status = models.CharField(
		max_length=16,
		choices=CouponDispatchJobStatus.choices,
		default=CouponDispatchJobStatus.PENDING,
		db_index=True,
		verbose_name='Статус',
	)
	total_phones = models.PositiveIntegerField(default=0, verbose_name='Телефонов в исходных данных')
	unique_phones = models.PositiveIntegerField(default=0, verbose_name='Уникальных валидных телефонов')
	guests_found = models.PositiveIntegerField(default=0, verbose_name='Найдено гостей')
	available_coupons = models.PositiveIntegerField(default=0, verbose_name='Доступных купонов на старте')
	coupons_assigned = models.PositiveIntegerField(default=0, verbose_name='Назначено купонов')
	errors_count = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
	mobile_api_sent = models.BooleanField(default=False, verbose_name='Отправлено в mobile API')
	mobile_api_sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Время отправки в mobile API')
	mobile_api_response = models.JSONField(default=dict, blank=True, verbose_name='Ответ mobile API')
	error_log = models.TextField(blank=True, verbose_name='Лог ошибок')
	started_at = models.DateTimeField(null=True, blank=True, verbose_name='Начало обработки')
	finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Конец обработки')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		ordering = ('-created_at',)
		verbose_name = 'Задача рассылки купонов'
		verbose_name_plural = 'Задачи рассылки купонов'

	def __str__(self) -> str:
		return f'#{self.id} | {self.title} | {self.status}'


class CouponDispatchJobResult(models.Model):
	job = models.ForeignKey(
		CouponDispatchJob,
		on_delete=models.CASCADE,
		related_name='results',
		verbose_name='Задача рассылки',
	)
	phone_raw = models.CharField(max_length=64, blank=True, verbose_name='Телефон (как введен)')
	phone_normalized = models.CharField(max_length=32, blank=True, db_index=True, verbose_name='Телефон (normalized)')
	guest_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True, verbose_name='ID гостя')
	coupon_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True, verbose_name='ID купона')
	coupon_code = models.CharField(max_length=128, blank=True, verbose_name='Код купона')
	success = models.BooleanField(default=False, db_index=True, verbose_name='Успех')
	error_message = models.TextField(blank=True, verbose_name='Текст ошибки')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

	class Meta:
		ordering = ('id',)
		indexes = [
			models.Index(fields=('job', 'success'), name='idx_coup_job_success'),
		]
		verbose_name = 'Результат рассылки купона'
		verbose_name_plural = 'Результаты рассылки купонов'

	def __str__(self) -> str:
		return f'job={self.job_id} phone={self.phone_normalized} success={self.success}'
