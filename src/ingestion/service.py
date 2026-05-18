from typing import Literal, List, Dict
from fastapi import UploadFile
from ..backgroundJobs import tasks

class IngestionService:

    @staticmethod
    def process_files(
        domain: Literal['email', 'policy', 'payment', 'ticket', 'feature', 'report'],
        file_paths: List[str],
        creation_date: str = None,
        isLegacy: bool = False,
        status: str = 'active',
        department: str = None,
        project_codename: str = None
    ):
        return DomainFileProcessor(
            domain, 
            file_paths, 
            creation_date=creation_date,
            isLegacy=isLegacy,
            status=status,
            department=department,
            project_codename=project_codename
        ).process()


class DomainFileProcessor:
    
    def __init__(
        self, 
        domain: Literal['email', 'policy', 'payment', 'ticket', 'feature', 'report'], 
        file_paths: List[str],
        creation_date: str = None,
        isLegacy: bool = False,
        status: str = 'active',
        department: str = None,
        project_codename: str = None
    ):
        self.domain = domain
        self.file_paths = file_paths
        self.creation_date = creation_date
        self.isLegacy = isLegacy
        self.status = status
        self.department = department
        self.project_codename = project_codename
        
        # Map domains directly to the Celery task objects
        self._handlers = {
            'email': tasks.process_email,
            'policy': tasks.process_policy,
            'payment': tasks.process_payment,
            'ticket': tasks.process_ticket,
            'feature': tasks.process_feature,
            'report': tasks.process_report
        }

    def process(self):
        handler = self._handlers.get(self.domain)
        if not handler:
            raise ValueError("Invalid domain")
        
        # Dispatch the task to the respective Celery queue asynchronously
        # `.delay()` returns an AsyncResult object. We can return the task IDs.
        results = [
            handler.delay(
                p, 
                creation_date=self.creation_date,
                isLegacy=self.isLegacy,
                status=self.status,
                department=self.department,
                project_codename=self.project_codename
            ) for p in self.file_paths
        ]
        
        return [r.id for r in results]