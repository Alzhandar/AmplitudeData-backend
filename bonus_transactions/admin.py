from django.contrib import admin
from django.http import HttpRequest
from django.db.utils import OperationalError, ProgrammingError

from bonus_transactions.models import BonusTransactionJob, BonusTransactionJobResult, BonusTransactionSettings


@admin.register(BonusTransactionJob)
class BonusTransactionJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'status',
        'amount',
        'start_date',
        'expiration_date',
        'cashbacks_created',
        'errors_count',
        'created_at',
    )
    list_filter = ('status', 'input_source', 'start_date', 'expiration_date')
    search_fields = ('description', 'source_text', 'base_id_prefix')
    readonly_fields = (
        'created_at',
        'updated_at',
        'started_at',
        'finished_at',
        'total_phones',
        'unique_phones',
        'guests_found',
        'cashbacks_created',
        'errors_count',
        'error_log',
        'external_api_response',
    )


@admin.register(BonusTransactionJobResult)
class BonusTransactionJobResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'phone_normalized', 'guest_id', 'success', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('phone_raw', 'phone_normalized', 'doc_guid', 'base_id', 'error_message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BonusTransactionSettings)
class BonusTransactionSettingsAdmin(admin.ModelAdmin):
    list_display = ('base_id_prefix', 'updated_at')
    readonly_fields = ('singleton_guard', 'created_at', 'updated_at')

    def has_add_permission(self, request: HttpRequest) -> bool:
        try:
            if BonusTransactionSettings.objects.exists():
                return False
        except (ProgrammingError, OperationalError):
            # Table can be absent before migrations are applied.
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request: HttpRequest, obj: BonusTransactionSettings | None = None) -> bool:
        return False
