import os
from celery import Celery
from kombu import Queue, Exchange
from dotenv import load_dotenv

load_dotenv()

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_mysql_url = os.getenv("CELERY_BACKEND_URL", "db+mysql+pymysql://root:hello%40123@localhost:3306/orbitflow")

celery_app = Celery(
    "PayflowRAG",
    broker=_redis_url,
    backend=_mysql_url,
    include=['src.backgroundJobs.tasks']
)

celery_app.conf.update(
    task_acks_late=True,                 # Don't acknowledge until task completes successfully
    worker_prefetch_multiplier=1,        # Prevents one worker from hoarding tasks
    task_default_queue='default',
)

celery_app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('email', Exchange('email'), routing_key='email'),
    Queue('policy', Exchange('policy'), routing_key='policy'),
    Queue('payment', Exchange('payment'), routing_key='payment'),
    Queue('ticket', Exchange('ticket'), routing_key='ticket'),
    Queue('feature', Exchange('feature'), routing_key='feature'),
    Queue('report', Exchange('report'), routing_key='report')
)

celery_app.conf.task_routes = {
    'process_email_task': {'queue': 'email'},
    'process_policy_task': {'queue': 'policy'},
    'process_payment_task': {'queue': 'payment'},
    'process_ticket_task': {'queue': 'ticket'},
    'process_feature_task': {'queue': 'feature'},
    'process_report_task': {'queue': 'report'},
}