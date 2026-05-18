"""
Base interface for all chunking strategies.

To add a new strategy:
1. Create a new file in this directory
2. Subclass BaseChunkingStrategy
3. Implement the `chunk()` method
4. Register it in __init__.py's STRATEGIES dict
"""

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass, field


@dataclass
class ChunkResult:
    """Standardized output from any chunking strategy.

    Every strategy must produce a list of these, regardless of how
    the underlying parsing / splitting works.
    """
    text: str
    metadata: dict = field(default_factory=dict)


class BaseChunkingStrategy(ABC):
    """Interface that every chunking strategy must implement."""

    @abstractmethod
    def chunk(self, file_path: str) -> List[ChunkResult]:
        """Given a file path, return a list of ChunkResult objects.

        The strategy is responsible for:
        - Loading / parsing the file
        - Splitting it into chunks
        - Attaching relevant metadata (headings, pages, type, source, etc.)
        """
        ...
