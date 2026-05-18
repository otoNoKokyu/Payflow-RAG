from typing import Optional
from .service import ProcessPolicy
from .service import ProcessPayment
from .service import ProcessReport
from .celery_config import celery_app
# pyrefly: ignore [missing-import]
from celery.exceptions import SoftTimeLimitExceeded
import traceback


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
def process_email(self, file_path: str, creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    # Synchronous processing logic for email
    print(f"Celery Worker processing email from {file_path}")
    return {"status": "success", "domain": "email", "file": file_path}

@celery_app.task(name='process_policy_task', **base_task_kwargs)
def process_policy(self, file_path: str, chunking_strategy: str = "docling", creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    try:
        print(f"Starting to process policy file: {file_path} (strategy={chunking_strategy}, date={creation_date})")
        service = ProcessPolicy(
            file_path, 
            chunking_strategy=chunking_strategy, 
            creation_date=creation_date,
            isLegacy=isLegacy,
            status=status,
            department=department,
            project_codename=project_codename
        )
        service.process()
        print(f"Successfully processed policy file: {file_path}")
        return {"status": "success", "domain": "policy", "file": file_path, "strategy": chunking_strategy, "creation_date": creation_date}
    except Exception as e:
        print(f"ERROR processing policy file {file_path}: {e}")
        traceback.print_exc()
        raise e

@celery_app.task(name='process_payment_task', **base_task_kwargs)
def process_payment(self, file_path: str, creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    try:
        print(f"Starting to process payment file: {file_path}")
        service = ProcessPayment(file_path) # Payment processing logic might not use creation_date yet, but we accept it
        service.process()
        print(f"Successfully processed payment file: {file_path}")
        return {"status": "success", "domain": "payment", "file": file_path, "creation_date": creation_date}
    except Exception as e:
        print(f"ERROR processing payment file {file_path}: {e}")
        traceback.print_exc()
        raise e

@celery_app.task(name='process_ticket_task', **base_task_kwargs)
def process_ticket(self, file_path: str, creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    print(f"Celery Worker processing ticket from {file_path}")
    return {"status": "success", "domain": "ticket", "file": file_path}

@celery_app.task(name='process_feature_task', **base_task_kwargs)
def process_feature(self, file_path: str, creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    print(f"Celery Worker processing feature from {file_path}")
    return {"status": "success", "domain": "feature", "file": file_path}

@celery_app.task(name='process_report_task', **base_task_kwargs)
def process_report(self, file_path: str, chunking_strategy: str = "docling", creation_date: Optional[str] = None, isLegacy: bool = False, status: str = 'active', department: Optional[str] = None, project_codename: Optional[str] = None):
    try:
        print(f"Starting to process report file: {file_path} (strategy={chunking_strategy}, date={creation_date})")
        service = ProcessReport(
            file_path, 
            chunking_strategy=chunking_strategy, 
            creation_date=creation_date,
            isLegacy=isLegacy,
            status=status,
            department=department,
            project_codename=project_codename
        )
        service.process()
        print(f"Successfully processed report file: {file_path}")
        return {"status": "success", "domain": "report", "file": file_path, "strategy": chunking_strategy, "creation_date": creation_date}
    except Exception as e:
        print(f"ERROR processing report file {file_path}: {e}")
        traceback.print_exc()
        raise e