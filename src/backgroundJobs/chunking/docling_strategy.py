"""
Docling-based chunking strategy.

Uses Docling's DocumentConverter for parsing and HierarchicalChunker
for structure-aware splitting. Supports PDF, DOCX, and other formats
that Docling handles natively.
"""

from typing import List, cast

from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import BaseChunkingStrategy, ChunkResult


class DoclingChunkingStrategy(BaseChunkingStrategy):
    """Structure-aware chunking using Docling's HierarchicalChunker.

    This strategy preserves document hierarchy (headings, sections)
    and extracts rich metadata (page numbers, element types) from
    the parsed document. It also uses an adaptive fallback to split
    mega-chunks into smaller sub-chunks, preserving context.
    """

    def __init__(self, max_length: int = 2000, overlap: int = 300):
        self._converter = DocumentConverter()
        self._chunker = HierarchicalChunker()
        self.max_length = max_length
        self.overlap = overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_length,
            chunk_overlap=self.overlap
        )

    def chunk(self, file_path: str) -> List[ChunkResult]:
        """Convert a document and split it into hierarchical chunks.

        Args:
            file_path: Absolute path to the document file.

        Returns:
            List of ChunkResult with text and metadata (headings, pages,
            chunk_type, source filename).
        """
        # 1. Parse the document
        conv_result = self._converter.convert(file_path)
        doc = conv_result.document

        # 2. Chunk using hierarchical structure
        raw_chunks = self._chunker.chunk(doc)

        # 3. Normalize into ChunkResult objects
        results: List[ChunkResult] = []
        for chunk in raw_chunks:
            # Fix: Use cast to satisfy strict type checking for str.join
            headings = " > ".join(cast(List[str], chunk.meta.headings)) if chunk.meta.headings else ""

            # Check if chunk needs fallback splitting
            if len(chunk.text) > self.max_length:
                # Apply adaptive fallback (Fallback 1 & 2 handled automatically)
                sub_chunks = self._splitter.split_text(chunk.text)
                for sub_chunk in sub_chunks:
                    # Preserve context on every sub-chunk
                    final_text = f"[Context: {headings}]\n\n{sub_chunk}" if headings else sub_chunk
                    results.append(ChunkResult(text=final_text))
            else:
                # Normal path
                final_text = f"[Context: {headings}]\n\n{chunk.text}" if headings else chunk.text
                results.append(ChunkResult(text=final_text))

        return results
