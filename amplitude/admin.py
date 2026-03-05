from django.contrib import admin
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html

from .common import AmplitudeEventTranslations
from .models import (
    AmplitudeSyncSchedule,
    BigDataPhoneDaySyncState,
    BigDataVisit,
    DailyDeviceActivity,
    DeviceVisitTime,
    MobileSession,
)

admin.site.site_header = 'Панель администратора'
admin.site.site_title = 'Админка'
admin.site.index_title = 'Управление системой'


class HasDeviceFilter(admin.SimpleListFilter):
    title = 'Есть устройство'
    parameter_name = 'has_device'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(device_id='')
        if self.value() == 'no':
            return queryset.filter(device_id='')
        return queryset


class HasUserFilter(admin.SimpleListFilter):
    title = 'Есть пользователь'
    parameter_name = 'has_user'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(user_id='')
        if self.value() == 'no':
            return queryset.filter(user_id='')
        return queryset


class HasEventTypeFilter(admin.SimpleListFilter):
    title = 'Есть событие'
    parameter_name = 'has_event_type'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(event_type='')
        if self.value() == 'no':
            return queryset.filter(event_type='')
        return queryset


class EventTypeRuFilter(admin.SimpleListFilter):
    title = 'Тип события'
    parameter_name = 'event_type_ru'

    def lookups(self, request, model_admin):
        raw_event_types = (
            model_admin.get_queryset(request)
            .exclude(event_type='')
            .order_by()
            .values_list('event_type', flat=True)
            .distinct()
        )

        deduped = {}
        for event_type in raw_event_types:
            normalized = (event_type or '').strip()
            if not normalized:
                continue
            deduped.setdefault(normalized, normalized)

        sorted_events = sorted(
            deduped.keys(),
            key=lambda name: AmplitudeEventTranslations.translate(name).lower(),
        )

        return [
            (event_type, AmplitudeEventTranslations.translate(event_type))
            for event_type in sorted_events
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(event_type=self.value())
        return queryset


@admin.register(MobileSession)
class MobileSessionAdmin(admin.ModelAdmin):
    list_display = (
        'event_time',
        'event_type',
        'event_type_ru',
        'user_id',
        'device_id',
        'phone_number',
        'platform',
        'device_brand',
        'device_manufacturer',
        'device_model',
    )
    list_filter = ('date', 'platform', EventTypeRuFilter, HasEventTypeFilter, HasDeviceFilter, HasUserFilter)
    search_fields = ('user_id', 'device_id', 'phone_number', 'insert_id', 'device_brand', 'device_model')

    @admin.display(description='Событие (рус.)')
    def event_type_ru(self, obj):
        return AmplitudeEventTranslations.translate(obj.event_type)


class DeviceVisitTimeInline(admin.TabularInline):
    model = DeviceVisitTime
    extra = 0
    fields = ('event_time', 'created_at')
    readonly_fields = ('event_time', 'created_at')
    can_delete = False
    ordering = ('-event_time',)


@admin.register(DailyDeviceActivity)
class DailyDeviceActivityAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'device_id',
        'phone_number',
        'platform',
        'device_brand',
        'device_manufacturer',
        'device_model',
        'visits_count',
        'device_visit_times_link',
        'first_seen',
        'last_seen',
    )
    list_filter = ('date', 'platform', HasDeviceFilter, HasUserFilter)
    search_fields = ('user_id', 'device_id', 'phone_number', 'device_brand', 'device_model')
    inlines = (DeviceVisitTimeInline,)

    @admin.display(description='ВРЕМЕНА ВИЗИТОВ УСТРОЙСТВ')
    def device_visit_times_link(self, obj):
        base_url = reverse('admin:amplitude_devicevisittime_changelist')
        query_string = urlencode({'daily_activity__id__exact': obj.id})
        url = f'{base_url}?{query_string}'
        return format_html('<a href="{}">Открыть</a>', url)


@admin.register(DeviceVisitTime)
class DeviceVisitTimeAdmin(admin.ModelAdmin):
    list_display = ('daily_activity', 'event_time', 'created_at')
    list_filter = ('daily_activity__date', 'event_time')
    search_fields = ('daily_activity__device_id', 'daily_activity__phone_number')


@admin.register(AmplitudeSyncSchedule)
class AmplitudeSyncScheduleAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'last_run_at', 'updated_at')
    fields = ('enabled', 'last_run_at')
    readonly_fields = ('last_run_at',)

    def has_add_permission(self, request):
        return not AmplitudeSyncSchedule.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BigDataVisit)
class BigDataVisitAdmin(admin.ModelAdmin):
    list_display = ('time_create', 'bigdata_visit_id', 'guest_phone_normalized', 'guest_phone_raw', 'updated_at')
    list_filter = ('time_create',)
    search_fields = ('bigdata_visit_id', 'guest_phone_raw', 'guest_phone_normalized')


@admin.register(BigDataPhoneDaySyncState)
class BigDataPhoneDaySyncStateAdmin(admin.ModelAdmin):
    list_display = ('date', 'phone_normalized', 'result_count', 'synced_at')
    list_filter = ('date',)
    search_fields = ('phone_normalized',)
