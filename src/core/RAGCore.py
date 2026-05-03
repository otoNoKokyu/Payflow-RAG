import os
import requests
import uuid
from typing import List

from google import genai
from google.genai import types
from pinecone import Pinecone

# ---------------------------------------------------------------------------
# Module-level clients — initialized once per process, naturally singleton,
# thread-safe, no footguns.
# ---------------------------------------------------------------------------

_genai_client = genai.Client(api_key='AIzaSyDmway9ZkhcOG0WaAKWjI4yYQHL7Q62Hm8')
_pc = Pinecone(api_key='pcsk_VrS7J_GdXZACVvbm6pSaAoPy1VZeAhpykCkGqU61krs7z12bxmANdcyDmHb3cRfRLfGPz')

INDEX_NAME = "payflow"


# ---------------------------------------------------------------------------
# Pure functions — no shared mutable state, easy to test, easy to reuse.
# ---------------------------------------------------------------------------

def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of text chunks and return their vectors using local Ollama."""
    print(f"Embedding {len(texts)} chunks with local Ollama...")
    url = "http://localhost:11434/api/embed"
    payload = {
        "model": "qwen3-embedding:0.6b",
        "input": texts
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    embeddings = response.json().get('embeddings', [])
    
    # Qwen embeddings use Matryoshka Representation Learning (MRL), 
    # which means we can simply slice the vectors to our required dimension (1024)
    # to perfectly match our Pinecone index without losing meaningful performance.
    # Note: Cast to float because Pinecone strictly checks types and json might parse exact 0s as ints.
    return [[float(val) for val in emb[:1024]] for emb in embeddings]


def store(texts: List[dict],namespace:str) -> None:
    """Embed texts and upsert them into the vector index."""
    if not texts:
        return
        
    index = _pc.Index(INDEX_NAME)
    
    # Pinecone's inference API has a batch size limit of 96
    batch_size = 96
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        index.upsert_records(
            namespace=namespace,
            records=batch
        )


def retrieve(query: str, top_k: int = 5) -> List[str]:
    """Embed a query and return the top-k matching texts from the index."""
    query_vector = embed([query])[0]
    index = _pc.Index(INDEX_NAME)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
    )

    return [
        match["metadata"]["text"]
        for match in results.get("matches", [])
        if "metadata" in match and "text" in match["metadata"]
    ]


async def generate(query: str, context_docs: List[str]) -> str:
    """Build a prompt from retrieved docs and stream an LLM answer."""
    context = "\n".join(context_docs)
    prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    
    # Use the asynchronous aio wrapper for Gemini
    response = await _genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


async def query(query_text: str) -> str:
    """Full RAG pipeline: retrieve relevant docs then generate an answer."""
    docs = retrieve(query_text)
    return await generate(query_text, docs)