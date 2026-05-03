from fastapi import UploadFile, File, Form
from typing import List, Literal
from ..core.AppExceptions import AppBaseException

async def validated_file(
    files: List[UploadFile] = File(..., description="List of files to upload (max 3 files)"),
    domain: Literal['email', 'policy', 'payment', 'ticket', 'feature'] = Form(..., description="Description of the upload")
) -> dict:
    MAX_SIZE = 1024 * 1024  # 1MB
    
    if not files or len(files) == 0:
        raise AppBaseException("At least one file must be provided", 400)
    
    if len(files) > 3:
        raise AppBaseException("Maximum 3 files allowed", 400)
        
    if not domain or len(domain.strip()) == 0:
        raise AppBaseException("domain cannot be empty", 400)
        
    for file in files:
        # file.size is available in FastAPI 0.99.0+
        if file.size is not None and file.size > MAX_SIZE:
            raise AppBaseException(f"File {file.filename} is too large. Max size is 1MB.", 400) 
            
    return {"files": files, "domain": domain}