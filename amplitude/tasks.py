from celery import shared_task
from django.db import transaction
from django.utils import timezone

from amplitude.models import AmplitudeSyncSchedule
from amplitude.services.sync_service import AmplitudeSyncService


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def sync_amplitude_today(self):
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
        schedule.last_run_at = now
        schedule.save(update_fields=['last_run_at', 'updated_at'])
        return {'status': 'ok', 'result': result}
