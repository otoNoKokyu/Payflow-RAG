from fastapi import APIRouter, FastAPI

from .ingestion.router import ingestionRouter
from .core.AppExceptions import setup_exception_handlers


app = FastAPI()
setup_exception_handlers(app)
app.include_router(ingestionRouter)



@app.get('/')
def read_root():
    return {"hello":1}
