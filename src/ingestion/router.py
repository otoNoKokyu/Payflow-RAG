from fastapi import APIRouter, Depends, UploadFile
from ..core.BaseResponse import WrappedRouter
from .models import validated_file
from typing import Annotated

ingestionRouter = WrappedRouter(prefix="/ingest")


@ingestionRouter.get("/supported-formats")
def supportedFileFormats():
    return ['okokok']


@ingestionRouter.post("")
def ingest_documents(
    validated_data: dict = Depends(validated_file),
):
    files = validated_data["files"]
    description = validated_data["description"]
    
    return {
        "file_count": len(files),
        "description": description,
        "files": [f.filename for f in files],
    }