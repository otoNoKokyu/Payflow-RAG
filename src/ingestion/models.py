from fastapi import UploadFile, File, Form
from typing import List, Literal
from ..core.AppExceptions import AppBaseException

async def validated_file(
    files: List[UploadFile] = File(..., description="List of files to upload (max 3 files)"),
    domain: Literal['email', 'policy', 'payment', 'ticket', 'feature', 'report'] = Form(..., description="Description of the upload"),
    creation_date: str = Form(None, description="Creation date of the document"),
    isLegacy: bool = Form(False),
    status: Literal['active', 'inactive'] = Form('active'),
    department: str = Form(None),
    project_codename: str = Form(None)
) -> dict:
    
    if not files or len(files) == 0:
        raise AppBaseException("At least one file must be provided", 400)
    
    if len(files) > 3:
        raise AppBaseException("Maximum 3 files allowed", 400)
        
    if not domain or len(domain.strip()) == 0:
        raise AppBaseException("domain cannot be empty", 400)
        
    if domain == 'policy' and (not creation_date or len(creation_date.strip()) == 0):
        raise AppBaseException("creation_date is mandatory for policy documents", 400)

    return {
        "files": files,
        "domain": domain,
        "creation_date": creation_date,
        "isLegacy": isLegacy,
        "status": status,
        "department": department,
        "project_codename": project_codename
    }