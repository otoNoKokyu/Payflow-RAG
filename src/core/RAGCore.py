import os
import uuid
import logging
from typing import List, Optional

from dotenv import load_dotenv
from .llm_provider import get_llm_provider
from .query_rewriter import rewrite_query, SubQuery
from .prompts import GENERATOR_SYSTEM_PROMPTS
from pinecone import Pinecone

load_dotenv()

# ---------------------------------------------------------------------------
# Module-level clients — initialized once per process, naturally singleton,
# thread-safe, no footguns.
# ---------------------------------------------------------------------------

_llm = get_llm_provider()
_pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

INDEX_NAME = "payflow"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions — no shared mutable state, easy to test, easy to reuse.
# ---------------------------------------------------------------------------

def store(texts: List[dict],namespace:str) -> None:
    """Embed texts and upsert them into the vector index manually."""
    if not texts:
        return
        
    # Write chunks to a file in src/chunks for inspection
    try:
        # Extract filename from source metadata or generate one
        base_filename = texts[0].get('source') or texts[0].get('filename') or f"chunks_{namespace}_{uuid.uuid4().hex[:8]}"
        # Ensure it ends with .md
        if base_filename.endswith('.pdf') or base_filename.endswith('.txt'):
            base_filename = os.path.splitext(base_filename)[0]
        filename = f"{base_filename}.md"
        
        # Path to src/chunks (relative to src/core/RAGCore.py)
        chunks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        file_path = os.path.join(chunks_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Document Chunks: {base_filename}\n")
            f.write(f"Total Chunks: {len(texts)}\n\n")
            for i, item in enumerate(texts):
                f.write(f"### Chunk {i}\n")
                f.write(item.get('text', ''))
                f.write("\n\n---\n\n")
        print(f"DEBUG: Saved structured chunks to {file_path}")
    except Exception as e:
        print(f"DEBUG: Failed to save chunks to file: {e}")

    index = _pc.Index(INDEX_NAME)
    
    # Prepare records for integrated inference upsert
    records = []
    for item in texts:
        # Integrated inference requires _id instead of id
        record = {
            "_id": item.get('id', str(uuid.uuid4())),
        }
        for k, v in item.items():
            if k != 'id':
                # Sanitize metadata: Pinecone supports string, number, bool, or list of strings
                if isinstance(v, list):
                    record[k] = [str(i) for i in v]
                elif isinstance(v, (str, int, float, bool)) or v is None:
                    record[k] = v
                else:
                    record[k] = str(v)
        records.append(record)
    
    # Pinecone standard batch size for upsert_records
    batch_size = 96
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        index.upsert_records(
            namespace=namespace,
            records=batch
        )


def retrieve(query: str, namespace: str, top_k: int = 5, filters: Optional[dict] = None) -> List[str]:
    """Search for relevant docs and re-rank using Pinecone's integrated reranker for diversity.
    
    Args:
        query:     The search query text.
        namespace: Pinecone namespace to search in.
        top_k:     Number of initial candidates (before reranking).
        filters:   Optional Pinecone metadata filter dict (e.g. {"status": {"$eq": "active"}}).
    """
    index = _pc.Index(INDEX_NAME)

    # Build the query dict — filters go inside it for integrated inference
    query_dict = {"inputs": {"text": query}, "top_k": 50}
    if filters:
        query_dict["filter"] = filters

    results = index.search(
        namespace=namespace,
        query=query_dict,
        rerank={"model": "bge-reranker-v2-m3", "rank_fields": ["text"], "top_n": 10}
    )

    response_dict = results.to_dict()
    hits = response_dict.get("result", {}).get("hits", [])
    
    return [hit.get("fields", {}).get("text") for hit in hits if hit.get("fields", {}).get("text")]


async def generate(query: str, context_docs: List[str], namespace: str = "default") -> tuple[str, int]:
    """Build a prompt from retrieved docs and stream an LLM answer."""
    context = "\n".join(context_docs)
    prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    
    system_prompt = GENERATOR_SYSTEM_PROMPTS.get(namespace, GENERATOR_SYSTEM_PROMPTS["default"])
    
    response = await _llm.generate(prompt=prompt, system_prompt=system_prompt)
    return response.text, response.prompt_tokens


async def query(query_text: str, namespace: str) -> tuple[str, List[str], int, List[dict]]:
    """Full RAG pipeline: rewrite query → retrieve → generate.
    
    Returns:
        (answer, docs, prompt_tokens, sub_queries)
        sub_queries is a list of dicts with 'rewritten_query' and 'filters' keys
        for observability/debugging.
    """
    # Step 1: Rewrite the query using the lightweight model
    sub_queries = await rewrite_query(query_text, namespace, _llm)
    logger.info("Query rewritten into %d sub-queries: %s", len(sub_queries), sub_queries)

    # Use RAGDebugger to print the rewritten query information to the terminal console
    from .debugger import RAGDebugger
    RAGDebugger.log_rewritten_queries(query_text, sub_queries)

    # Step 2: Retrieve for each sub-query
    all_docs: List[str] = []
    seen: set = set()
    for sq in sub_queries:
        docs = retrieve(sq.rewritten_query, namespace=namespace, filters=sq.filters or None)
        for doc in docs:
            if doc not in seen:
                seen.add(doc)
                all_docs.append(doc)

    # Step 3: Generate answer using the ORIGINAL query (not the rewritten ones)
    answer, tokens = await generate(query_text, all_docs, namespace)

    # Serialize sub-queries for the response
    sub_queries_serialized = [
        {"rewritten_query": sq.rewritten_query, "filters": sq.filters}
        for sq in sub_queries
    ]

    # Save the pipeline trace using RAGDebugger to debug.info file
    RAGDebugger.write_debug_file(
        query_text=query_text,
        namespace=namespace,
        sub_queries=sub_queries,
        docs=all_docs,
        tokens=tokens,
        answer=answer
    )

    return answer, all_docs, tokens, sub_queries_serialized