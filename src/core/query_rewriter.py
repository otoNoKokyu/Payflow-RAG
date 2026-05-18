"""
Query Rewriter — LLM-powered query decomposition and metadata-aware rewriting.

Pluggable provider architecture:
  - Primary: Google GenAI (gemini-3-flash-preview)
  - Fallback: Local Ollama (llama3.1:8b)

Set REWRITER_PROVIDER env var to "ollama" to use local Ollama,
or "genai" (default) for Google GenAI.

This module sits between the user's raw question and RAGCore.retrieve(),
improving retrieval accuracy without changing the downstream generation.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .llm_provider import get_llm_provider, LLMProvider
from .prompts import REWRITER_SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata Schema Registry
# ---------------------------------------------------------------------------
# Tells the rewriter LLM exactly what filterable fields exist per namespace.
# Derived from what ProcessPayment, ProcessPolicy, and ProcessReport store
# in their post_tokenize() methods (see backgroundJobs/service.py).
#
# Keys:   namespace name (matches Pinecone namespace)
# Values: dict of field_name -> {type, description, example_values}
# ---------------------------------------------------------------------------

METADATA_SCHEMA = {
    "payment": {
        "type": {
            "field_type": "string",
            "description": "Kind of payment record",
            "allowed_values": [
                "individual",
                "daily_summary",
                "weekly_summary",
                "monthly_summary",
                "currency_summary",
                "status_summary",
            ],
        },
        "period_type": {
            "field_type": "string",
            "description": "Granularity of the record",
            "allowed_values": ["exact", "day", "week", "month", "all_time"],
        },
        "payment_id": {
            "field_type": "string",
            "description": "Unique payment identifier",
            "example": "PAY-001",
        },
        "date_str": {
            "field_type": "string",
            "description": "Human-readable exact date for individual records",
            "example": "15th may 2024",
        },
        "start_date": {
            "field_type": "string",
            "description": "Human-readable start date of the period (for summaries)",
            "example": "1st january 2024",
        },
        "end_date": {
            "field_type": "string",
            "description": "Human-readable end date of the period (for summaries)",
            "example": "31st january 2024",
        },
        "amount": {
            "field_type": "number",
            "description": "Transaction amount as a float",
            "example": 250.00,
        },
        "currency": {
            "field_type": "string",
            "description": "ISO currency code",
            "example_values": ["USD", "EUR", "GBP", "INR"],
        },
        "status": {
            "field_type": "string",
            "description": "Payment status",
            "example_values": ["completed", "failed", "pending", "refunded"],
        },
        "count": {
            "field_type": "integer",
            "description": "Number of payments in a summary record",
            "example": 42,
        },
    },
    "policy": {
        "type": {
            "field_type": "string",
            "description": "Always 'policy' for this namespace",
            "allowed_values": ["policy"],
        },
        "source": {
            "field_type": "string",
            "description": "Original filename of the document",
            "example_values": [
                "Support_SOP_v3_1_2.pdf",
                "PayFlow_Refund_Policy_v3.2.docx",
                "Deltacare_Insurance_policy.pdf",
                "Legacy_Support_SOP_v1.4.pdf",
                "PayFlow_Refund_Policy_v2.7_LEGACY.docx",
                "a-plus-health-insurance-policy-wording.pdf",
            ],
        },
        "isLegacy": {
            "field_type": "boolean",
            "description": "Whether this is a legacy/outdated document",
        },
        "status": {
            "field_type": "string",
            "description": "Document status",
            "allowed_values": ["active", "inactive"],
        },
        "department": {
            "field_type": "string",
            "description": "Department that owns this document (may be null)",
            "example_values": ["support", "finance", "compliance"],
        },
        "project_codename": {
            "field_type": "string",
            "description": "Internal project codename (may be null)",
        },
        "creation_date": {
            "field_type": "string",
            "description": "Document creation date (may be null)",
            "example": "2026-01-15",
        },
    },
    "report": {
        "type": {
            "field_type": "string",
            "description": "Always 'report' for this namespace",
            "allowed_values": ["report"],
        },
        "source": {
            "field_type": "string",
            "description": "Original filename of the report",
            "example_values": [
                "denmark-ant-corruption-report.pdf",
                "spain-anto-corruption-report.pdf",
                "f4a6c658-en.pdf",
            ],
        },
        "isLegacy": {
            "field_type": "boolean",
            "description": "Whether this is a legacy/outdated document",
        },
        "status": {
            "field_type": "string",
            "description": "Document status",
            "allowed_values": ["active", "inactive"],
        },
        "department": {
            "field_type": "string",
            "description": "Department that owns this document (may be null)",
        },
        "project_codename": {
            "field_type": "string",
            "description": "Internal project codename (may be null)",
        },
        "creation_date": {
            "field_type": "string",
            "description": "Document creation date (may be null)",
        },
    },
}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class SubQuery:
    """A single decomposed and rewritten sub-query with optional filters."""
    rewritten_query: str
    filters: Optional[dict] = field(default_factory=dict)



def _build_user_prompt(query: str, namespace: str) -> str:
    """Build the user prompt with the query and the namespace's metadata schema."""
    schema = METADATA_SCHEMA.get(namespace, {})
    schema_text = json.dumps(schema, indent=2, default=str)

    return (
        f"Namespace: {namespace}\n\n"
        f"Available metadata fields for filtering:\n```json\n{schema_text}\n```\n\n"
        f"User query: \"{query}\"\n\n"
        f"Rewrite this query into sub-queries with optional metadata filters. "
        f"Respond ONLY with a JSON object containing a \"sub_queries\" array. No other text."
    )


# ---------------------------------------------------------------------------
# Main rewrite function
# ---------------------------------------------------------------------------

async def rewrite_query(
    query: str,
    namespace: str,
    llm_provider: Optional[LLMProvider] = None,
) -> List[SubQuery]:
    """Rewrite a user query into focused sub-queries with optional metadata filters.

    Uses the provider configured by the centralized llm_provider system.

    Args:
        query:        The raw user question.
        namespace:    The Pinecone namespace (payment, policy, report).
        llm_provider: Optional LLMProvider instance. If not provided, gets default.

    Returns:
        A list of SubQuery objects. On any failure, returns a single SubQuery
        containing the original query with no filters (graceful degradation).
    """
    # Fallback: original query, no filters
    fallback = [SubQuery(rewritten_query=query, filters={})]

    # Skip rewriting for unknown namespaces
    if namespace not in METADATA_SCHEMA:
        logger.warning("Unknown namespace '%s' — skipping query rewrite", namespace)
        return fallback

    try:
        provider = llm_provider or get_llm_provider()
        user_prompt = _build_user_prompt(query, namespace)

        logger.info(f"Rewriter Prompt: {user_prompt}")

        system_prompt = REWRITER_SYSTEM_PROMPTS.get(namespace, REWRITER_SYSTEM_PROMPTS["default"])

        response = await provider.generate(
            prompt=user_prompt, 
            system_prompt=system_prompt, 
            json_mode=True
        )

        logger.info(f"Rewriter Output: {response.text}")

        # Parse the structured JSON response
        raw = json.loads(response.text)
        sub_queries_raw = raw.get("sub_queries", [])

        if not sub_queries_raw:
            logger.warning("Rewriter returned empty sub_queries — using fallback")
            return fallback

        # Cap at 3 sub-queries
        sub_queries_raw = sub_queries_raw[:3]

        result = []
        for sq in sub_queries_raw:
            rewritten = sq.get("rewritten_query", "").strip()
            filters = sq.get("filters", {})

            # Skip empty rewrites
            if not rewritten:
                continue

            # Clean up empty filter dicts and None values
            cleaned_filters = {
                k: v for k, v in filters.items()
                if v is not None and v != {}
            } if filters else {}

            result.append(SubQuery(rewritten_query=rewritten, filters=cleaned_filters))

        return result if result else fallback

    except json.JSONDecodeError as e:
        logger.error("Failed to parse rewriter JSON response: %s", e)
        return fallback
    except Exception as e:
        logger.error("Query rewriter failed (%s): %s", type(e).__name__, e, exc_info=True)
        return fallback
