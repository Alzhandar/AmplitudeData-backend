import logging

from celery import shared_task

from notifications.choices import NotificationType
from notifications.services.birthday_flow import KidBirthdayFlowService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def collect_kid_birthdays_task(self):
    logger.debug('collect_kid_birthdays_task_started')
    result = KidBirthdayFlowService().collect_due_birthdays(notification_type=NotificationType.HB_KIDS)
    logger.info(
        'collect_kid_birthdays_task_finished',
        extra={
            'birthdays_created': result.created,
            'birthdays_updated': result.updated,
            'birthdays_skipped': result.skipped,
        },
    )
    return {
        'created': result.created,
        'updated': result.updated,
        'skipped': result.skipped,
    }


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def dispatch_kid_birthday_notifications_task(self):
    logger.debug('dispatch_kid_birthday_notifications_task_started')
    return KidBirthdayFlowService().dispatch_due_notifications(notification_type=NotificationType.HB_KIDS)
