from django.contrib import admin

from coupon_dispatch.models import CouponDispatchJob, CouponDispatchJobResult


class CouponDispatchJobResultInline(admin.TabularInline):
	model = CouponDispatchJobResult
	extra = 0
	fields = ('phone_raw', 'phone_normalized', 'guest_id', 'coupon_id', 'coupon_code', 'success', 'error_message')
	readonly_fields = fields
	can_delete = False
	show_change_link = False


@admin.register(CouponDispatchJob)
class CouponDispatchJobAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'title',
		'initiated_by',
		'dispatch_mode',
		'marketing_sale_id',
		'valid_until',
		'status',
		'total_phones',
		'guests_found',
		'available_coupons',
		'coupons_assigned',
		'errors_count',
		'mobile_api_sent',
		'created_at',
	)
	list_filter = ('status', 'mobile_api_sent', 'created_at')
	search_fields = ('title', 'marketing_sale_name', 'error_log', 'initiated_by__email')
	readonly_fields = (
		'dispatch_mode',
		'valid_until',
		'status',
		'total_phones',
		'unique_phones',
		'guests_found',
		'available_coupons',
		'coupons_assigned',
		'errors_count',
		'mobile_api_sent',
		'mobile_api_sent_at',
		'mobile_api_response',
		'error_log',
		'started_at',
		'finished_at',
		'created_at',
		'updated_at',
	)
	inlines = (CouponDispatchJobResultInline,)


@admin.register(CouponDispatchJobResult)
class CouponDispatchJobResultAdmin(admin.ModelAdmin):
	list_display = ('job', 'phone_normalized', 'guest_id', 'coupon_id', 'coupon_code', 'success', 'created_at')
	list_filter = ('success', 'created_at')
	search_fields = ('phone_raw', 'phone_normalized', 'coupon_code', 'error_message')
