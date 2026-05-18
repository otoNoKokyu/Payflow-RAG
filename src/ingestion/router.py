from .service import IngestionService
from fastapi import Depends
from ..core.BaseResponse import WrappedRouter
from .models import validated_file
import os
import anyio

from ..core.database import get_db
from ..core.models import DocumentRegistry
from sqlalchemy.orm import Session

# Define RawData path relative to this file
RAW_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

ingestionRouter = WrappedRouter(prefix="/ingest")


@ingestionRouter.get("/supported-formats")
def supportedFileFormats():
    return ['okokok']


@ingestionRouter.post("")
async def ingest_documents(validated_data: dict = Depends(validated_file), db: Session = Depends(get_db)):
    domain = validated_data["domain"]
    files = validated_data["files"]
    creation_date = validated_data.get("creation_date")
    isLegacy = validated_data.get("isLegacy")
    status_val = validated_data.get("status")
    department = validated_data.get("department")
    project_codename = validated_data.get("project_codename")
    
    domain_path = os.path.join(RAW_DATA_DIR, domain)
    os.makedirs(domain_path, exist_ok=True)
    
    file_paths = []
    for file in files:
        # Check if document already exists and archive the old one
        old_docs = db.query(DocumentRegistry).filter_by(filename=file.filename, domain=domain, status="active").all()
        for old_doc in old_docs:
            old_doc.status = "archived"
        
        # Insert the new document record
        new_doc = DocumentRegistry(
            filename=file.filename, 
            domain=domain, 
            status=status_val,
            creation_date=creation_date,
            is_legacy=isLegacy,
            department=department,
            project_codename=project_codename
        )
        db.add(new_doc)
        
        file_path = os.path.join(domain_path, file.filename)
        file_paths.append(file_path)
        
        CHUNK_SIZE = 204800  # 200KB
        async with await anyio.open_file(file_path, mode="wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                await f.write(chunk)
        
        await file.seek(0)
    
    db.commit()

    IngestionService.process_files(
        domain,
        file_paths,
        creation_date=creation_date,
        isLegacy=isLegacy,
        status=status_val,
        department=department,
        project_codename=project_codename
    )
    return 'files ingested successfully'



    