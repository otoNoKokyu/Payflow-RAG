import os
from celery import Celery
from kombu import Queue, Exchange

celery_app = Celery(
    "CompanyRAG",
    broker="redis://localhost:6379/0",
    backend="db+mysql://root:Arko%409876@localhost:3306/orbitflow",
    include=['CompanyRAG.src.backgroundJobs.tasks']
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
    Queue('feature', Exchange('feature'), routing_key='feature')
)

celery_app.conf.task_routes = {
    'process_email_task': {'queue': 'email'},
    'process_policy_task': {'queue': 'policy'},
    'process_payment_task': {'queue': 'payment'},
    'process_ticket_task': {'queue': 'ticket'},
    'process_feature_task': {'queue': 'feature'},
}