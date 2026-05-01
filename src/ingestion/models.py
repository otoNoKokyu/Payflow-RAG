from fastapi import UploadFile, File, Form
from typing import List
from ..core.AppExceptions import BusinessLogicError

async def validated_file(
    files: List[UploadFile] = File(..., description="List of files to upload (max 3 files)"),
    description: str = Form(..., min_length=1, description="Description of the upload")
) -> dict:
    MAX_SIZE = 1024 * 1024  # 1MB
    
    if not files or len(files) == 0:
        raise BusinessLogicError("At least one file must be provided", 400)
    
    if len(files) > 3:
        raise BusinessLogicError("Maximum 3 files allowed", 400)
        
    if not description or len(description.strip()) == 0:
        raise BusinessLogicError("Description cannot be empty", 400)
        
    for file in files:
        # file.size is available in FastAPI 0.99.0+
        if file.size is not None and file.size > MAX_SIZE:
            raise BusinessLogicError(f"File {file.filename} is too large. Max size is 1MB.", 400) 
            
    return {"files": files, "description": description}