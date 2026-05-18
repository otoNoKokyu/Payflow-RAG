from fastapi import Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Literal
import os
from ..core.RAGCore import query as rag_query
from ..core.BaseResponse import WrappedRouter

ragRouter = WrappedRouter(prefix="/rag")

class QueryRequest(BaseModel):
    question: str
    type: Literal['policy', 'payment', 'report']
    chunks: bool = False
    debug: bool = False

@ragRouter.post("/query")
async def execute_query(request: QueryRequest):
    """
    Execute a RAG query based on the question and domain type.
    """
    answer, docs, tokens, sub_queries = await rag_query(request.question, namespace=request.type)
    
    response = {
        "question": request.question,
        "type": request.type,
        "answer": answer,
        "tokens": tokens,
        "rewritten_query": sub_queries[0]["rewritten_query"] if sub_queries else None,
        "rewritten_queries": sub_queries
    }
    
    if request.chunks:
        response["chunks"] = docs
        
    return response

@ragRouter.get("/demo")
async def get_demo():
    """
    Serve the RAG demo HTML page.
    """
    demo_path = os.path.join(os.path.dirname(__file__), "demo.html")
    return FileResponse(demo_path)

@ragRouter.get("/upload")
async def get_upload():
    """
    Serve the RAG demo HTML page.
    """
    demo_path = os.path.join(os.path.dirname(__file__), "demo.html")
    return FileResponse(demo_path)
