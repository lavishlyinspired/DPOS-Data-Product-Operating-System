"""
Document Processor
Processes various document formats for knowledge extraction.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import json
import re


@dataclass
class DocumentChunk:
    """A chunk of document content."""
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    source: str


@dataclass
class ProcessedDocument:
    """A fully processed document."""
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    format: str
    source_path: str


class DocumentProcessor:
    """
    Processes documents into chunks for knowledge extraction.
    Supports: Plain text, Markdown, JSON, and basic structure extraction.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.

        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: str) -> ProcessedDocument:
        """
        Process a file and return chunks.

        Args:
            file_path: Path to the file

        Returns:
            ProcessedDocument with chunks
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine format
        suffix = path.suffix.lower()

        if suffix in ['.txt', '.md', '.markdown']:
            return self._process_text_file(path)
        elif suffix == '.json':
            return self._process_json_file(path)
        else:
            # Try as text
            return self._process_text_file(path)

    def process_text(self, text: str, source: str = "text") -> ProcessedDocument:
        """
        Process raw text into chunks.

        Args:
            text: The text content
            source: Source identifier

        Returns:
            ProcessedDocument with chunks
        """
        chunks = self._chunk_text(text, source)

        return ProcessedDocument(
            chunks=chunks,
            metadata={"char_count": len(text), "chunk_count": len(chunks)},
            format="text",
            source_path=source
        )

    def _process_text_file(self, path: Path) -> ProcessedDocument:
        """Process a text/markdown file."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = self._chunk_text(content, str(path))

        # Extract metadata from markdown if present
        metadata = self._extract_markdown_metadata(content)
        metadata["file_name"] = path.name
        metadata["char_count"] = len(content)
        metadata["chunk_count"] = len(chunks)

        return ProcessedDocument(
            chunks=chunks,
            metadata=metadata,
            format="markdown" if path.suffix in ['.md', '.markdown'] else "text",
            source_path=str(path)
        )

    def _process_json_file(self, path: Path) -> ProcessedDocument:
        """Process a JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert JSON to text representation
        if isinstance(data, list):
            chunks = []
            for i, item in enumerate(data):
                chunk_text = json.dumps(item, indent=2)
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    metadata={"item_index": i},
                    chunk_index=i,
                    source=str(path)
                ))
        else:
            # Single object - chunk the string representation
            text = json.dumps(data, indent=2)
            chunks = self._chunk_text(text, str(path))

        return ProcessedDocument(
            chunks=chunks,
            metadata={"file_name": path.name, "type": "json"},
            format="json",
            source_path=str(path)
        )

    def _chunk_text(self, text: str, source: str) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []

        # Try to split by paragraphs first
        paragraphs = text.split('\n\n')

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        content=current_chunk.strip(),
                        metadata={},
                        chunk_index=chunk_index,
                        source=source
                    ))
                    chunk_index += 1

                    # Keep overlap
                    if self.chunk_overlap > 0:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    # Single paragraph exceeds chunk size - split by sentences
                    sub_chunks = self._split_long_text(para, source, chunk_index)
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_chunk = ""
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add remaining content
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                metadata={},
                chunk_index=chunk_index,
                source=source
            ))

        return chunks

    def _split_long_text(self, text: str, source: str, start_index: int) -> List[DocumentChunk]:
        """Split a long text that exceeds chunk size."""
        chunks = []

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current = ""
        idx = start_index

        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size:
                if current:
                    chunks.append(DocumentChunk(
                        content=current.strip(),
                        metadata={},
                        chunk_index=idx,
                        source=source
                    ))
                    idx += 1
                current = sentence
            else:
                current = current + " " + sentence if current else sentence

        if current:
            chunks.append(DocumentChunk(
                content=current.strip(),
                metadata={},
                chunk_index=idx,
                source=source
            ))

        return chunks

    def _extract_markdown_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from markdown frontmatter if present."""
        metadata = {}

        # Check for YAML frontmatter
        if content.startswith('---'):
            try:
                end = content.index('---', 3)
                frontmatter = content[3:end].strip()

                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            except ValueError:
                pass

        # Extract headers
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        if headers:
            metadata["headers"] = headers[:10]

        return metadata
