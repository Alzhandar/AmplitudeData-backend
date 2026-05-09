import logging

from celery import shared_task

from bonus_transactions.services.bonus_transaction_service import BonusTransactionService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_bonus_transaction_job(self, job_id: int):
    logger.info('task_started', extra={'job_id': job_id})
    service = BonusTransactionService()
    service.process_job(job_id)
