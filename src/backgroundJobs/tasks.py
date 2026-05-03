from CompanyRAG.src.backgroundJobs.service import ProcessPayment
from .celery_config import celery_app
from celery.exceptions import SoftTimeLimitExceeded

RETRYABLE_EXCEPTIONS = (
    SoftTimeLimitExceeded,
)

base_task_kwargs = {
    'bind': True,
    'autoretry_for': RETRYABLE_EXCEPTIONS,
    'retry_kwargs': {'max_retries': 5},
    'retry_backoff': True,
    'retry_backoff_max': 600,
    'soft_time_limit': 300,
    'time_limit': 360
}

@celery_app.task(name='process_email_task', **base_task_kwargs)
def process_email(self, file_path: str):
    # Synchronous processing logic for email
    print(f"Celery Worker processing email from {file_path}")
    return {"status": "success", "domain": "email", "file": file_path}

@celery_app.task(name='process_policy_task', **base_task_kwargs)
def process_policy(self, file_path: str):
    print(f"Celery Worker processing policy from {file_path}")
    return {"status": "success", "domain": "policy", "file": file_path}

@celery_app.task(name='process_payment_task', **base_task_kwargs)
def process_payment(self, file_path: str):
    import traceback
    try:
        print(f"Starting to process payment file: {file_path}")
        service = ProcessPayment(file_path)
        service.process()
        print(f"Successfully processed payment file: {file_path}")
        return {"status": "success", "domain": "payment", "file": file_path}
    except Exception as e:
        print(f"ERROR processing payment file {file_path}: {e}")
        traceback.print_exc()
        raise e

@celery_app.task(name='process_ticket_task', **base_task_kwargs)
def process_ticket(self, file_path: str):
    print(f"Celery Worker processing ticket from {file_path}")
    return {"status": "success", "domain": "ticket", "file": file_path}

@celery_app.task(name='process_feature_task', **base_task_kwargs)
def process_feature(self, file_path: str):
    print(f"Celery Worker processing feature from {file_path}")
    return {"status": "success", "domain": "feature", "file": file_path}