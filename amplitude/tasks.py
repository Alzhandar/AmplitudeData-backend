import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from amplitude.models import AmplitudeSyncSchedule, DailyDeviceActivity
from amplitude.services.bigdata_visit_service import BigDataVisitSyncService
from amplitude.services.sync_service import AmplitudeSyncService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def sync_amplitude_today(self):
    logger.info('sync_amplitude_today_started')
    service = AmplitudeSyncService()
    return service.sync_today_mobile_events()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def run_scheduled_sync(self):
    with transaction.atomic():
        schedule, _ = AmplitudeSyncSchedule.objects.select_for_update().get_or_create(
            pk=1,
            defaults={'enabled': True},
        )

        if not schedule.enabled:
            return {'status': 'skipped', 'reason': 'disabled'}

        now = timezone.localtime(timezone.now())
        current_hour_start = now.replace(minute=0, second=0, microsecond=0)
        if schedule.last_run_at and schedule.last_run_at >= current_hour_start:
            return {'status': 'skipped', 'reason': 'already_ran_this_hour', 'hour': current_hour_start.isoformat()}

        result = AmplitudeSyncService().sync_today_mobile_events()
        today = timezone.localdate()
        phones = list(
            DailyDeviceActivity.objects.filter(date=today)
            .exclude(phone_number='')
            .values_list('phone_number', flat=True)
            .distinct()
        )
        bigdata_result = BigDataVisitSyncService().sync_visits(
            start_date=today,
            end_date=today,
            phones=phones,
        )
        schedule.last_run_at = now
        schedule.save(update_fields=['last_run_at', 'updated_at'])
        return {'status': 'ok', 'result': result, 'bigdata': bigdata_result}
