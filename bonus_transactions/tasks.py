from celery import shared_task

from bonus_transactions.services.bonus_transaction_service import BonusTransactionService


@shared_task(bind=True)
def process_bonus_transaction_job(self, job_id: int):
    service = BonusTransactionService()
    service.process_job(job_id)
