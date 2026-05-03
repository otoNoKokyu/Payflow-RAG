from typing import Literal, List, Dict
from fastapi import UploadFile
from ..backgroundJobs import tasks

class IngestionService:

    @staticmethod
    def process_files(
        domain: Literal['email', 'policy', 'payment', 'ticket', 'feature'],
        file_paths: List[str]
    ):
        return DomainFileProcessor(domain, file_paths).process()


class DomainFileProcessor:
    
    def __init__(self, domain: Literal['email', 'policy', 'payment', 'ticket', 'feature'], file_paths: List[str]):
        self.domain = domain
        self.file_paths = file_paths
        
        # Map domains directly to the Celery task objects
        self._handlers = {
            'email': tasks.process_email,
            'policy': tasks.process_policy,
            'payment': tasks.process_payment,
            'ticket': tasks.process_ticket,
            'feature': tasks.process_feature
        }

    def process(self):
        handler = self._handlers.get(self.domain)
        if not handler:
            raise ValueError("Invalid domain")
        
        # Dispatch the task to the respective Celery queue asynchronously
        # `.delay()` returns an AsyncResult object. We can return the task IDs.
        results = [handler.delay(p) for p in self.file_paths]
        
        return [r.id for r in results]