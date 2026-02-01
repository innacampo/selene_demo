#!/usr/bin/env python3
"""
PDF to JSON Extractor for ChromaDB RAG
Extracts text from PDFs, chunks intelligently, and exports in ChromaDB-ready format.
"""

import os
import json
import logging
import hashlib
import tempfile
import signal
import re
from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError:
    raise ImportError("Please install pypdf: pip install pypdf")

try:
    import nltk

    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    SENTENCE_TOKENIZER_AVAILABLE = True
except ImportError:
    SENTENCE_TOKENIZER_AVAILABLE = False
    logging.warning("nltk not available. Falling back to basic chunking.")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class ChunkConfig:
    """Configuration for text chunking optimized for RAG."""

    chunk_size: int = 1500
    overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000

    def __post_init__(self):
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0 or self.overlap >= self.chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size")


@dataclass
class ProcessingConfig:
    """Configuration for PDF processing."""

    allowed_base_dir: Optional[Path] = None
    output_dir: Path = Path("./output")
    timeout_seconds: int = 60
    max_file_size_mb: int = 100
    collection_name: str = "knowledge_base"

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
        if self.allowed_base_dir:
            self.allowed_base_dir = Path(self.allowed_base_dir).resolve()


@dataclass
class ChromaExport:
    """Export format matching ChromaDB's add() method signature."""

    ids: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    metadatas: list[dict] = field(default_factory=list)

    def add(self, doc_id: str, document: str, metadata: dict):
        self.ids.append(doc_id)
        self.documents.append(document)
        self.metadatas.append(self._validate_metadata(metadata))

    def _validate_metadata(self, metadata: dict) -> dict:
        """Ensure metadata values are ChromaDB-compatible (str, int, float, bool)."""
        validated = {}
        for key, value in metadata.items():
            if value is None:
                validated[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                validated[key] = value
            elif isinstance(value, (list, tuple)):
                validated[key] = ", ".join(str(v) for v in value)
            else:
                validated[key] = str(value)
        return validated

    def to_dict(self) -> dict:
        return {
            "ids": self.ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
        }

    def __len__(self) -> int:
        return len(self.ids)


# ============================================================================
# Utilities
# ============================================================================


class ProcessingTimeout(Exception):
    pass


@contextmanager
def timeout(seconds: int):
    """Timeout context manager (Unix only, no-op on Windows)."""

    def handler(signum, frame):
        raise ProcessingTimeout(f"Operation timed out after {seconds}s")

    if hasattr(signal, "SIGALRM"):
        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield


def validate_path(
    path: Path, allowed_base: Optional[Path] = None, must_exist: bool = True
) -> Path:
    """Validate path and prevent directory traversal."""
    resolved = path.resolve()
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    if allowed_base:
        try:
            resolved.relative_to(allowed_base.resolve())
        except ValueError:
            raise PermissionError(
                f"Access denied: {resolved} outside allowed directory"
            )
    return resolved


def file_hash(filepath: Path) -> str:
    """Calculate truncated SHA256 hash of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return len(text) // 4


# ============================================================================
# Text Processing
# ============================================================================


def clean_text(text: str) -> str:
    """Clean text for better embedding quality."""
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"[-_]{3,}", "---", text)
    text = re.sub(r"\b[Pp]age\s*\d+(\s*of\s*\d+)?\b", "", text)
    text = re.sub(r"https?://\S+", "[URL]", text)
    text = re.sub(r"\S+@\S+\.\S+", "[EMAIL]", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    return text.strip()


def chunk_text(text: str, config: ChunkConfig) -> Generator[str, None, None]:
    """Chunk text preserving sentence boundaries when possible."""
    text = clean_text(text)
    if not text:
        return

    if SENTENCE_TOKENIZER_AVAILABLE:
        yield from _sentence_chunker(text, config)
    else:
        yield from _word_boundary_chunker(text, config)


def _sentence_chunker(text: str, config: ChunkConfig) -> Generator[str, None, None]:
    """Chunk by sentences."""
    sentences = nltk.sent_tokenize(text)
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sent_len = len(sentence)

        # Long sentence: flush current chunk, then split sentence
        if sent_len > config.max_chunk_size:
            if current_chunk:
                chunk = " ".join(current_chunk)
                if len(chunk) >= config.min_chunk_size:
                    yield chunk
                current_chunk, current_len = [], 0

            yield from _word_boundary_chunker(sentence, config)
            continue

        # Would exceed chunk size: yield and start new with overlap
        if current_len + sent_len + 1 > config.chunk_size and current_chunk:
            chunk = " ".join(current_chunk)
            if len(chunk) >= config.min_chunk_size:
                yield chunk

            # Keep sentences for overlap
            overlap_chunk, overlap_len = [], 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) + 1 <= config.overlap:
                    overlap_chunk.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current_chunk, current_len = overlap_chunk, overlap_len

        current_chunk.append(sentence)
        current_len += sent_len + (1 if len(current_chunk) > 1 else 0)

    # Final chunk
    if current_chunk:
        chunk = " ".join(current_chunk)
        if len(chunk) >= config.min_chunk_size:
            yield chunk


def _word_boundary_chunker(
    text: str, config: ChunkConfig
) -> Generator[str, None, None]:
    """Fallback chunker splitting at word boundaries."""
    words = text.split()
    current_chunk = []
    current_len = 0

    for word in words:
        word_len = len(word)
        potential_len = current_len + word_len + (1 if current_chunk else 0)

        if potential_len > config.chunk_size and current_chunk:
            chunk = " ".join(current_chunk)
            if len(chunk) >= config.min_chunk_size:
                yield chunk

            # Overlap
            overlap_words, overlap_len = [], 0
            for w in reversed(current_chunk):
                if overlap_len + len(w) + 1 <= config.overlap:
                    overlap_words.insert(0, w)
                    overlap_len += len(w) + 1
                else:
                    break
            current_chunk, current_len = overlap_words, overlap_len

        current_chunk.append(word)
        current_len += word_len + (1 if len(current_chunk) > 1 else 0)

    if current_chunk:
        chunk = " ".join(current_chunk)
        if len(chunk) >= config.min_chunk_size:
            yield chunk


# ============================================================================
# PDF Processing
# ============================================================================


def extract_pdf_text(filepath: Path, config: ProcessingConfig) -> tuple[str, dict]:
    """Extract text and metadata from PDF."""
    size_mb = filepath.stat().st_size / (1024 * 1024)
    if size_mb > config.max_file_size_mb:
        raise ValueError(
            f"File too large: {size_mb:.1f}MB > {config.max_file_size_mb}MB"
        )

    with timeout(config.timeout_seconds):
        reader = PdfReader(str(filepath))

        # Extract metadata
        metadata = {"filename": filepath.name, "page_count": len(reader.pages)}
        if reader.metadata:
            if reader.metadata.title:
                metadata["title"] = str(reader.metadata.title)[:500]
            if reader.metadata.author:
                metadata["author"] = str(reader.metadata.author)[:200]

        # Extract text
        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Page {page_num} extraction failed: {e}")

        return " ".join(text_parts), metadata


def process_pdf(
    filepath: Path, chunk_config: ChunkConfig, processing_config: ProcessingConfig
) -> Generator[tuple[str, str, dict], None, None]:
    """Process PDF and yield (id, document, metadata) tuples."""
    logger.info(f"Processing: {filepath.name}")

    try:
        fhash = file_hash(filepath)
        text, pdf_meta = extract_pdf_text(filepath, processing_config)

        if not text.strip():
            logger.warning(f"No text in {filepath.name}")
            return

        base_meta = {
            "source": filepath.name,
            "source_type": "pdf",
            "file_hash": fhash,
            "collection": processing_config.collection_name,
            "ingested_at": datetime.utcnow().isoformat(),
            **pdf_meta,
        }

        chunks = list(chunk_text(text, chunk_config))
        total = len(chunks)

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{fhash}_{idx:04d}"
            meta = {
                **base_meta,
                "chunk_index": idx,
                "total_chunks": total,
                "char_count": len(chunk),
                "estimated_tokens": estimate_tokens(chunk),
            }
            yield chunk_id, chunk, meta

        logger.info(f"Created {total} chunks from {filepath.name}")

    except ProcessingTimeout:
        logger.error(f"Timeout: {filepath.name}")
    except PdfReadError as e:
        logger.error(f"Invalid PDF {filepath.name}: {e}")
    except Exception as e:
        logger.error(f"Error processing {filepath.name}: {e}")


# ============================================================================
# Main Export Function
# ============================================================================


def prepare_chromadb_export(
    pdf_folder: str | Path,
    output_filename: str = "chromadb_export.json",
    chunk_config: Optional[ChunkConfig] = None,
    processing_config: Optional[ProcessingConfig] = None,
) -> Path:
    """
    Process PDFs and export in ChromaDB-ready JSON format.

    Output structure:
    {
        "export_metadata": {...},
        "ids": [...],
        "documents": [...],
        "metadatas": [...]
    }

    Usage with ChromaDB:
        import chromadb, json

        client = chromadb.PersistentClient("./db")
        collection = client.get_or_create_collection("knowledge_base")

        with open("chromadb_export.json") as f:
            data = json.load(f)

        collection.add(
            ids=data["ids"],
            documents=data["documents"],
            metadatas=data["metadatas"]
        )
    """
    chunk_config = chunk_config or ChunkConfig()
    processing_config = processing_config or ProcessingConfig()

    # Validate input path
    pdf_folder = validate_path(
        Path(pdf_folder),
        allowed_base=processing_config.allowed_base_dir,
        must_exist=True,
    )
    if not pdf_folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {pdf_folder}")

    # Prepare output path
    safe_name = Path(output_filename).name
    if not safe_name.endswith(".json"):
        safe_name += ".json"
    processing_config.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = processing_config.output_dir / safe_name

    # Find PDFs
    pdf_files = sorted(f for f in pdf_folder.iterdir() if f.suffix.lower() == ".pdf")

    if not pdf_files:
        logger.warning(f"No PDFs found in {pdf_folder}")

    logger.info(f"Found {len(pdf_files)} PDF files")

    # Process
    export = ChromaExport()
    success_count, fail_count = 0, 0

    for pdf_file in pdf_files:
        try:
            docs = list(process_pdf(pdf_file, chunk_config, processing_config))
            if docs:
                for doc_id, document, metadata in docs:
                    export.add(doc_id, document, metadata)
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Failed {pdf_file.name}: {e}")
            fail_count += 1

    # Build final export
    export_data = {
        "export_metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "source_folder": str(pdf_folder),
            "files_processed": success_count,
            "files_failed": fail_count,
            "total_chunks": len(export),
            "collection_name": processing_config.collection_name,
            "chunk_config": {
                "chunk_size": chunk_config.chunk_size,
                "overlap": chunk_config.overlap,
                "min_chunk_size": chunk_config.min_chunk_size,
            },
        },
        **export.to_dict(),
    }

    # Atomic write
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        dir=processing_config.output_dir,
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(export_data, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)

    tmp_path.replace(output_path)

    logger.info(
        f"Created {output_path}: {len(export)} chunks from {success_count} files"
    )
    return output_path


# ============================================================================
# CLI
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract PDFs to ChromaDB-ready JSON format"
    )
    parser.add_argument("pdf_folder", help="Directory containing PDFs")
    parser.add_argument("-o", "--output", default="chromadb_export.json")
    parser.add_argument("--output-dir", default="./output")
    parser.add_argument("--collection", default="knowledge_base")
    parser.add_argument("--chunk-size", type=int, default=1500)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--min-chunk", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-size-mb", type=int, default=100)
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        output = prepare_chromadb_export(
            pdf_folder=args.pdf_folder,
            output_filename=args.output,
            chunk_config=ChunkConfig(
                chunk_size=args.chunk_size,
                overlap=args.overlap,
                min_chunk_size=args.min_chunk,
            ),
            processing_config=ProcessingConfig(
                output_dir=Path(args.output_dir),
                timeout_seconds=args.timeout,
                max_file_size_mb=args.max_size_mb,
                collection_name=args.collection,
            ),
        )
        print(f"Created: {output}")

    except KeyboardInterrupt:
        print("\nCancelled")
        exit(1)
    except Exception as e:
        logger.error(str(e))
        exit(1)


if __name__ == "__main__":
    main()
