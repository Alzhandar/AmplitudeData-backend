from django.db import models


class BonusTransactionJobStatus(models.TextChoices):
    PENDING = 'pending', 'Ожидает'
    PROCESSING = 'processing', 'В обработке'
    COMPLETED = 'completed', 'Завершено'
    FAILED = 'failed', 'Ошибка'


class BonusTransactionInputSource(models.TextChoices):
    MANUAL = 'manual', 'Ручной ввод'
    EXCEL = 'excel', 'Excel файл'
    MIXED = 'mixed', 'Смешанный'


class BonusTransactionSettings(models.Model):
    singleton_guard = models.BooleanField(default=True, unique=True, editable=False)
    base_id_prefix = models.CharField(max_length=255, default='bonus', verbose_name='Префикс base_id по умолчанию')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Настройки начисления бонусов'
        verbose_name_plural = 'Настройки начисления бонусов'

    def save(self, *args, **kwargs):
        self.singleton_guard = True
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'base_id_prefix={self.base_id_prefix}'


class BonusTransactionJob(models.Model):
    description = models.CharField(max_length=500, verbose_name='Причина начисления')
    amount = models.PositiveIntegerField(verbose_name='Сумма бонуса')
    start_date = models.DateField(db_index=True, verbose_name='Дата начала действия')
    expiration_date = models.DateField(db_index=True, verbose_name='Дата окончания действия')
    base_id_prefix = models.CharField(max_length=255, blank=True, verbose_name='base_id (префикс)')
    bonus_type = models.PositiveIntegerField(default=1, verbose_name='Тип бонуса (type)')
    registration_bonus = models.BooleanField(default=False, verbose_name='registration_bonus')

    initiated_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bonus_transaction_jobs',
        verbose_name='Инициатор',
    )
    input_source = models.CharField(
        max_length=16,
        choices=BonusTransactionInputSource.choices,
        default=BonusTransactionInputSource.MANUAL,
        verbose_name='Источник телефонов',
    )
    source_text = models.TextField(blank=True, verbose_name='Телефоны (ручной ввод)')
    source_file = models.FileField(upload_to='bonus_transactions/', null=True, blank=True, verbose_name='Excel файл')

    status = models.CharField(
        max_length=16,
        choices=BonusTransactionJobStatus.choices,
        default=BonusTransactionJobStatus.PENDING,
        db_index=True,
        verbose_name='Статус',
    )
    total_phones = models.PositiveIntegerField(default=0, verbose_name='Телефонов в исходных данных')
    unique_phones = models.PositiveIntegerField(default=0, verbose_name='Уникальных валидных телефонов')
    guests_found = models.PositiveIntegerField(default=0, verbose_name='Найдено гостей')
    cashbacks_created = models.PositiveIntegerField(default=0, verbose_name='Успешно начислено')
    errors_count = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
    external_api_response = models.JSONField(default=dict, blank=True, verbose_name='Ответ cashback API')
    error_log = models.TextField(blank=True, verbose_name='Лог ошибок')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Начало обработки')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Конец обработки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Задача начисления бонусов'
        verbose_name_plural = 'Задачи начисления бонусов'

    def __str__(self) -> str:
        return f'#{self.id} | amount={self.amount} | {self.status}'


class BonusTransactionJobResult(models.Model):
    job = models.ForeignKey(
        BonusTransactionJob,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='Задача начисления',
    )
    phone_raw = models.CharField(max_length=64, blank=True, verbose_name='Телефон (как введен)')
    phone_normalized = models.CharField(max_length=32, blank=True, db_index=True, verbose_name='Телефон (normalized)')
    guest_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True, verbose_name='ID гостя')
    doc_guid = models.CharField(max_length=64, blank=True, verbose_name='doc_guid')
    base_id = models.CharField(max_length=255, blank=True, verbose_name='base_id')
    success = models.BooleanField(default=False, db_index=True, verbose_name='Успех')
    error_message = models.TextField(blank=True, verbose_name='Текст ошибки')
    cashback_payload = models.JSONField(default=dict, blank=True, verbose_name='Отправленный payload')
    cashback_response = models.JSONField(default=dict, blank=True, verbose_name='Ответ cashback API')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        ordering = ('id',)
        indexes = [
            models.Index(fields=('job', 'success'), name='idx_bonus_job_success'),
        ]
        verbose_name = 'Результат начисления бонуса'
        verbose_name_plural = 'Результаты начисления бонусов'

    def __str__(self) -> str:
        return f'job={self.job_id} phone={self.phone_normalized} success={self.success}'
