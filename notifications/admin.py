from django.contrib import admin

from notifications.models import (
	KidBirthdayNotification,
	PushDispatchLog,
	NotificationSchedule,
	NotificationTemplate,
	StoryRecipientConfig,
)


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
	list_display = (
		'notification_type',
		'send_time',
		'queue_create_time',
		'enabled',
		'last_checked_at',
		'last_queue_entry_created_at',
		'updated_at',
	)
	list_filter = ('notification_type', 'enabled')
	search_fields = ('notification_type',)
	readonly_fields = ('last_checked_at', 'last_queue_entry_created_at', 'created_at', 'updated_at')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
	list_display = ('notification_type', 'title', 'notification_backend_type', 'enabled', 'updated_at')
	list_filter = ('notification_type', 'enabled')
	search_fields = ('title', 'body', 'title_kz', 'body_kz')


@admin.register(StoryRecipientConfig)
class StoryRecipientConfigAdmin(admin.ModelAdmin):
	list_display = ('notification_type', 'story_id', 'story_date', 'enabled', 'updated_at')
	list_filter = ('notification_type', 'enabled', 'story_date')
	search_fields = ('notification_type',)


@admin.register(KidBirthdayNotification)
class KidBirthdayNotificationAdmin(admin.ModelAdmin):
	list_display = (
		'schedule_date',
		'scheduled_for',
		'notification_type',
		'kid_id',
		'kid_name',
		'guest_id',
		'guest_phone',
		'sent',
		'sent_at',
		'processing_started_at',
		'story_created',
	)
	list_filter = ('notification_type', 'sent', 'story_created', 'schedule_date')
	search_fields = ('kid_id', 'kid_name', 'guest_id', 'guest_phone', 'last_error')
	readonly_fields = (
		'notification_type',
		'birthday_date',
		'kid_id',
		'kid_name',
		'guest_id',
		'guest_phone',
		'schedule_date',
		'scheduled_for',
		'sent',
		'sent_at',
		'processing_started_at',
		'story_created',
		'external_story_id',
		'last_error',
		'kid_payload',
		'guest_payload',
		'created_at',
		'updated_at',
	)

	def has_add_permission(self, request):
		return False


@admin.register(PushDispatchLog)
class PushDispatchLogAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'created_at',
		'initiated_by_email',
		'target',
		'city_id',
		'recipients_count',
		'notification_type',
		'notification_id',
		'status',
	)
	list_filter = ('status', 'target', 'notification_type', 'created_at')
	search_fields = ('initiated_by_email', 'title', 'body', 'error_message')
	readonly_fields = (
		'initiated_by',
		'initiated_by_email',
		'target',
		'city_id',
		'recipients_count',
		'title',
		'body',
		'title_kz',
		'body_kz',
		'notification_type',
		'survey_id',
		'review_id',
		'notification_id',
		'status',
		'error_message',
		'created_at',
		'updated_at',
	)

	def has_add_permission(self, request):
		return False
