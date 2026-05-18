import os
import logging
from typing import List

logger = logging.getLogger(__name__)

class RAGDebugger:
    """Centralized debugger class for RAG query pipeline monitoring, file logging, and console printouts."""
    
    @staticmethod
    def log_rewritten_queries(original_query: str, sub_queries: list) -> None:
        """Prints a highly visible query rewrite and filter debug summary to the terminal."""
        border = "=" * 70
        header = " QUERY REWRITER OBSERVABILITY INFO "
        
        print(f"\n{border}")
        print(f"{header:^70}")
        print(border)
        print(f"Original User Query : \"{original_query}\"")
        print(f"Decomposed Queries   : {len(sub_queries)} sub-query/queries generated")
        print("-" * 70)
        
        for idx, sq in enumerate(sub_queries, 1):
            if hasattr(sq, "rewritten_query"):
                rewritten = getattr(sq, "rewritten_query")
                filters = getattr(sq, "filters", {})
            elif isinstance(sq, dict):
                rewritten = sq.get("rewritten_query", "")
                filters = sq.get("filters", {})
            else:
                rewritten = str(sq)
                filters = {}
            
            print(f" [{idx}] Rewritten Query : \"{rewritten}\"")
            if filters:
                print(f"     Active Filters  : {filters}")
            else:
                print(f"     Active Filters  : None")
                
        print(f"{border}\n")

    @staticmethod
    def write_debug_file(
        query_text: str,
        namespace: str,
        sub_queries: list,
        docs: List[str],
        tokens: int,
        answer: str
    ) -> None:
        """Saves a structured debug.info trace file in the project root directory."""
        try:
            # Locate project root (assuming debugger.py is in src/core/)
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            debug_path = os.path.join(root_dir, "debug.info")
            
            with open(debug_path, "w", encoding="utf-8") as df:
                df.write("==================================================\n")
                df.write("RAG PIPELINE EXECUTION DEBUG INFO\n")
                df.write("==================================================\n")
                df.write(f"Original Query: {query_text}\n")
                df.write(f"Namespace:      {namespace}\n\n")
                
                df.write("--------------------------------------------------\n")
                df.write("Query Rewriter Sub-queries & Filters\n")
                df.write("--------------------------------------------------\n")
                if sub_queries:
                    for idx, sq in enumerate(sub_queries, 1):
                        if hasattr(sq, "rewritten_query"):
                            rewritten = getattr(sq, "rewritten_query")
                            filters = getattr(sq, "filters", {})
                        elif isinstance(sq, dict):
                            rewritten = sq.get("rewritten_query", "")
                            filters = sq.get("filters", {})
                        else:
                            rewritten = str(sq)
                            filters = {}
                        df.write(f"Sub-query {idx}:\n")
                        df.write(f"  Rewritten: \"{rewritten}\"\n")
                        df.write(f"  Filters:   {filters}\n\n")
                else:
                    df.write("No sub-queries generated.\n\n")
                    
                df.write("--------------------------------------------------\n")
                df.write("Retrieval Info\n")
                df.write("--------------------------------------------------\n")
                df.write(f"Total Unique Documents Retrieved: {len(docs)}\n\n")
                if docs:
                    for idx, doc in enumerate(docs, 1):
                        preview = (doc[:200] + '...') if len(doc) > 200 else doc
                        # Clean up double newlines in preview for compact display
                        preview_clean = "\n".join([line for line in preview.splitlines() if line.strip()])
                        df.write(f"Doc {idx} Preview:\n{preview_clean}\n\n")
                else:
                    df.write("No documents retrieved.\n\n")
                    
                df.write("--------------------------------------------------\n")
                df.write("Generation Info\n")
                df.write("--------------------------------------------------\n")
                df.write(f"Prompt Tokens Used: {tokens}\n")
                df.write(f"Final Answer:\n{answer}\n")
                df.write("==================================================\n")
                
            logger.info("Saved RAG pipeline execution trace to %s", debug_path)
        except Exception as ex:
            logger.error("Failed to write debug.info trace file: %s", ex)
