"""
Chunking strategy registry.

Usage:
    from ..chunking import get_strategy

    strategy = get_strategy()           # default: "docling"
    strategy = get_strategy("docling")  # explicit
    chunks   = strategy.chunk("/path/to/file.pdf")

To register a new strategy, add it to the STRATEGIES dict below.
"""

from typing import Dict, Optional, Type

from .base import BaseChunkingStrategy, ChunkResult
from .docling_strategy import DoclingChunkingStrategy

__all__ = [
    "BaseChunkingStrategy",
    "ChunkResult",
    "DoclingChunkingStrategy",
    "get_strategy",
    "STRATEGIES",
]

# ---------------------------------------------------------------------------
# Strategy registry — add new strategies here
# ---------------------------------------------------------------------------
STRATEGIES: Dict[str, Type[BaseChunkingStrategy]] = {
    "docling": DoclingChunkingStrategy,
}

DEFAULT_STRATEGY = "docling"


def get_strategy(name: Optional[str] = None) -> BaseChunkingStrategy:
    """Instantiate and return a chunking strategy by name.

    Args:
        name: Key in the STRATEGIES dict. Defaults to DEFAULT_STRATEGY.

    Returns:
        An instance of the requested strategy.

    Raises:
        ValueError: If the strategy name is not registered.
    """
    name = name or DEFAULT_STRATEGY
    cls = STRATEGIES.get(name)
    if cls is None:
        available = ", ".join(sorted(STRATEGIES.keys()))
        raise ValueError(
            f"Unknown chunking strategy: '{name}'. Available: [{available}]"
        )
    return cls()

