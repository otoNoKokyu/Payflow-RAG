from CompanyRAG.src.ingestion.service import IngestionService
from fastapi import Depends
from ..core.BaseResponse import WrappedRouter
from .models import validated_file
import os
import anyio

# Define RawData path relative to this file
RAW_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../RawData"))

ingestionRouter = WrappedRouter(prefix="/ingest")


@ingestionRouter.get("/supported-formats")
def supportedFileFormats():
    return ['okokok']


@ingestionRouter.post("")
async def ingest_documents(validated_data: dict = Depends(validated_file)):
    domain = validated_data["domain"]
    files = validated_data["files"]
    
    domain_path = os.path.join(RAW_DATA_DIR, domain)
    os.makedirs(domain_path, exist_ok=True)
    
    file_paths = []
    for file in files:
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

    IngestionService.process_files(
        domain,
        file_paths
    )
    return 'files ingested successfully'



    