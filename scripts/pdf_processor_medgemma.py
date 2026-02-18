"""
PDF Pre-processing and Chunking Module for MedGemma.

This module provides a specialized pipeline for preparing medical journal PDFs:
- High-fidelity text extraction using PyMuPDF (fitz).
- Scientific-grade cleaning (removing noise like citations, DOIs, and page artifacts).
- Section-aware chunking to preserve clinical context (headers like ABSTRACT, METHODS, etc.).
- Metadata generation for section-integrated RAG performance on small models.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    logger.warning("PyMuPDF not found. Install with: pip install pymupdf")


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract clean text from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Cleaned text content
    """
    logger.debug(f"extract_text_from_pdf: ENTER pdf_path={pdf_path}")
    if not HAS_FITZ:
        raise ImportError("PyMuPDF required. Install with: pip install pymupdf")

    try:
        doc = fitz.open(pdf_path)
        full_text = []

        for page_index, page in enumerate(doc):
            # Extract text blocks (preserves layout)
            blocks = page.get_text("blocks")

            page_text = []
            for block in blocks:
                if block[6] == 0:  # Text block (not image)
                    text = block[4].strip()
                    if text:
                        page_text.append(text)

            if page_text:
                full_text.append("\n\n".join(page_text))
                logger.debug(
                    f"extract_text_from_pdf: extracted page {page_index + 1} blocks={len(page_text)}"
                )

        doc.close()

        text = "\n\n".join(full_text)

        # Clean up PDF artifacts
        text = clean_pdf_text(text)
        logger.debug(f"extract_text_from_pdf: EXIT total_chars={len(text)}")
        return text

    except Exception as e:
        logger.exception("extract_text_from_pdf: failed to extract text from PDF")
        raise Exception(f"Error extracting text from PDF: {e}")


def clean_pdf_text(text: str) -> str:
    """
    Enhanced cleaning for medical journal PDFs to reduce prompt noise.
    Targets headers, footers, citations, and journal-specific metadata.
    """
    if not text:
        return ""

    # 1. Remove Bibliography/References (The biggest source of noise)
    # This splits at the first occurrence of "References" or "Bibliography"
    text = re.split(
        r"\n\s*(?:References|Bibliography|LITERATURE CITED|WORKS CITED)\s*\n",
        text,
        flags=re.IGNORECASE,
    )[0]

    # 2. Remove typical PDF headers/footers (e.g., "Page 1 of 20" or journal names)
    # Matches patterns like "Page 123", "Journal of Clinical...", "doi: 10.100..."
    text = re.sub(r"(?i)Page\s+\d+(\s+of\s+\d+)?", "", text)
    text = re.sub(r"(?i)doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+", "", text)
    text = re.sub(r"(?i)Copyright\s+©.*?\d{4}.*?\.", "", text)

    # 3. Clean Inline Citations (Stops MedGemma from getting stuck on names/years)
    # Matches (Author, 2023), [12, 14-16], (Smith et al., 2019)
    text = re.sub(r"\[\d+(?:,\s*\d+|-?\d+)*\]", "", text)  # Matches [12] or [1-5]
    text = re.sub(
        r"\(\s*[A-Z][a-z]+(?:\set\sal\.)?,\s*\d{4}\s*\)", "", text
    )  # Matches (Smith, 2020)

    # 4. Remove Table and Figure Captions
    # Often captions aren't useful without the image and just clutter the RAG
    text = re.sub(r"(?i)(?:Figure|Fig|Table)\s+\d+.*?\n", "", text)

    # 5. Final Formatting: Strip excessive whitespace
    text = re.sub(r"\s+", " ", text)  # Collapse multiple spaces/newlines
    text = re.sub(r"\n\s*\n", "\n", text)  # Remove empty lines

    return text.strip()


def chunk_text_medgemma(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 300,
) -> list[dict[str, str]]:
    """
    Split text into semantic chunks while tracking and injecting clinical sections.

    This function uses a sliding window approach with lookahead to detect section
    headers. It attempts to break chunks at paragraphs or sentence boundaries
    within a safe margin to avoid cutting off information mid-sentence.

    Args:
        text: The full cleaned text from the PDF.
        chunk_size: Target characters per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List[Dict[str, str]]: Chunks with "content" (labeled) and "section" metadata.
    """
    # Expanded regex to catch common medical journal section headers
    # \s* handles indentation, ^... ensures we catch lines starting with these keywords
    header_pattern = re.compile(
        r"^\s*(?:\d+\.?\s+)?(ABSTRACT|INTRODUCTION|METHODS|RESULTS|DISCUSSION|CONCLUSION|SAFETY|DOSAGE|ADVERSE EFFECTS|LIMITATIONS|TREATMENT|PARTICIPANTS)",
        re.IGNORECASE | re.MULTILINE,
    )

    chunks = []
    start = 0
    current_section = "Introduction"

    while start < len(text):
        # Determine initial end point
        end = min(start + chunk_size, len(text))

        # 1. Look ahead for section changes to update current_section
        # Looking slightly ahead (300 chars) helps detect if a new section starts right after this chunk
        search_window = text[start : min(end + 300, len(text))]
        headers = list(header_pattern.finditer(search_window))
        if headers:
            current_section = headers[0].group(1).title()

        # 2. Semantic boundary logic: Find a natural breakpoint (paragraph or sentence)
        if end < len(text):
            # Try to break at paragraph first
            para_break = text.rfind("\n\n", start + chunk_size - 400, end)
            if para_break != -1:
                end = para_break + 2
            else:
                # Fallback to sentence ending
                for punct in [". ", ".\n"]:
                    sent_end = text.rfind(punct, start + chunk_size - 300, end)
                    if sent_end != -1:
                        end = sent_end + len(punct)
                        break

        chunk_content = text[start:end].strip()
        if chunk_content:
            # Power Move: Explicitly label the content so the LLM identifies the context immediately
            # This is extremely effective for 4b parameter models with limited attention.
            labeled_content = f"[{current_section.upper()}] {chunk_content}"

            chunks.append({"content": labeled_content, "section": current_section})

        # Base case: we reached the end of the text
        if end >= len(text):
            break

        # Advance the window with overlap
        start = end - overlap

    logger.debug(
        f"chunk_text_medgemma: generated {len(chunks)} chunks (chunk_size={chunk_size}, overlap={overlap})"
    )
    return chunks


def create_source_name(filename: str) -> str:
    """
    Create clean source name from filename.

    Args:
        filename: Original PDF filename

    Returns:
        Clean source name
    """
    return Path(filename).stem


def process_pdf(pdf_path: str, chunk_size: int = 1500, overlap: int = 300) -> dict:
    """
    Process PDF file: extract text, remove references, create chunks.

    Args:
        pdf_path: Path to PDF file
        chunk_size: Chunk size in characters
        overlap: Overlap in characters

    Returns:
        Dictionary with source, chunks, and stats
    """
    if not HAS_FITZ:
        raise ImportError("PyMuPDF required. Install with: pip install pymupdf")

    pdf_path = Path(pdf_path)

    try:
        logger.debug(
            f"process_pdf: ENTER pdf_path={pdf_path}, chunk_size={chunk_size}, overlap={overlap}"
        )
        # Extract text
        full_text = extract_text_from_pdf(str(pdf_path))

        # Create source name from filename
        source = create_source_name(pdf_path.name)

        # Create chunks
        chunks = chunk_text_medgemma(full_text, chunk_size, overlap)

        # Get page count
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()

        logger.info(
            f"process_pdf: processed {pdf_path.name} pages={total_pages} chunks={len(chunks)} total_chars={len(full_text)}"
        )
        return {
            "source": source,
            "chunks": chunks,
            "filename": pdf_path.name,
            "total_pages": total_pages,
            "total_chars": len(full_text),
            "chunk_size": chunk_size,
            "overlap": overlap,
        }

    except Exception:
        logger.exception(f"process_pdf: Error processing {pdf_path}")
        return None


def process_pdfs_to_json(
    pdf_dir: str,
    output_file: str | None = None,
    chunk_size: int = 1500,
    overlap: int = 300,
    verbose: bool = True,
) -> dict:
    """
    Process all PDFs in directory for MedGemma knowledge base.

    Args:
        pdf_dir: Directory containing PDFs
        output_file: Output JSON filename (default: output/medgemma_kb_[timestamp].json)
        chunk_size: Chunk size in characters
        overlap: Overlap in characters
        verbose: Print progress

    Returns:
        Export data dictionary
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f"medgemma_kb_{timestamp}.json")
    else:
        # Ensure parent directory of explicit output file exists
        output_path = Path(output_file)
        if output_path.parent:
            output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf_dir = Path(pdf_dir)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"process_pdfs_to_json: No PDF files found in {pdf_dir}")
        print(f"No PDF files found in {pdf_dir}")
        return None

    if verbose:
        logger.info(
            f"process_pdfs_to_json: Processing {len(pdf_files)} PDF files (chunk_size={chunk_size} overlap={overlap})"
        )
        print(f"\n{'=' * 70}")
        print(f"Processing {len(pdf_files)} PDF files for MedGemma")
        print(f"Chunk size: {chunk_size} chars (~{chunk_size // 4} tokens)")
        print(f"Overlap: {overlap} chars (~{overlap // 4} tokens)")
        print(f"{'=' * 70}\n")

    all_ids = []
    all_documents = []
    all_metadatas = []

    for pdf_path in pdf_files:
        if verbose:
            logger.debug(f"process_pdfs_to_json: Processing {pdf_path.name}")
            print(f"Processing: {pdf_path.name}")

        result = process_pdf(str(pdf_path), chunk_size, overlap)

        if not result:
            logger.warning(
                f"process_pdfs_to_json: Skipping {pdf_path.name} due to processing error"
            )
            continue

        source = result["source"]

        if verbose:
            logger.debug(
                f"process_pdfs_to_json: result pages={result['total_pages']} chunks={len(result['chunks'])} chars={result['total_chars']}"
            )
            print(f"  Source: {source}")
            print(f"  Pages: {result['total_pages']}")
            print(f"  Chunks: {len(result['chunks'])}")
            print(f"  Avg chunk: {result['total_chars'] // len(result['chunks'])} chars")
            print()

        # Create entries for each chunk

        for i, chunk_dict in enumerate(result["chunks"]):
            chunk_id = f"{pdf_path.stem}_chunk_{i}"

            # Separate the text from the section dictionary
            document_text = chunk_dict["content"]
            section_label = chunk_dict["section"]

            metadata = {
                "source": source,
                "section": section_label,  # This is where the section lives!
                "filename": result["filename"],
                "chunk_index": i,
                "total_chunks": len(result["chunks"]),
                "total_pages": result["total_pages"],
                "chunk_size_chars": len(document_text),
            }

            all_ids.append(chunk_id)
            all_documents.append(document_text)  # Store only the text string
            all_metadatas.append(metadata)  # Store the dictionary metadata

    # Create export
    export_data = {
        "export_metadata": {
            "created_at": datetime.now().isoformat(),
            "files_processed": len(pdf_files),
            "total_chunks": len(all_ids),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "optimized_for": "MedGemma (128k context)",
            "mode": "simplified (filename as source, references removed)",
        },
        "ids": all_ids,
        "documents": all_documents,
        "metadatas": all_metadatas,
    }

    # Save to file
    if verbose:
        logger.info(f"process_pdfs_to_json: Writing {len(all_ids)} chunks to {output_file}")
        print(f"{'=' * 70}")
        print(f"Writing {len(all_ids)} chunks to {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    if verbose:
        logger.info("process_pdfs_to_json: Export complete")
        print("✓ Export complete!")
        print(f"{'=' * 70}\n")

    return export_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Simplified PDF processor for MedGemma (filename as source)"
    )
    parser.add_argument("pdf_path", help="PDF file or directory containing PDFs")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file (default: output/medgemma_kb_[timestamp].json)",
    )
    # Modified defaults for 4b optimization
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        help="Chunk size in characters (default: 2000 ~500 tokens)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=300,
        help="Overlap in characters (default: 300 ~75 tokens)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    path = Path(args.pdf_path)

    if path.is_file():
        # Single PDF
        result = process_pdf(str(path), args.chunk_size, args.overlap)
        if result:
            all_ids = []
            all_documents = []
            all_metadatas = []

            for i, chunk_dict in enumerate(result["chunks"]):
                chunk_id = f"{path.stem}_chunk_{i}"
                doc_text = chunk_dict["content"]
                section = chunk_dict["section"]

                all_ids.append(chunk_id)
                all_documents.append(doc_text)
                all_metadatas.append(
                    {
                        "source": result["source"],
                        "section": section,
                        "filename": result["filename"],
                        "chunk_index": i,
                        "total_chunks": len(result["chunks"]),
                        "total_pages": result["total_pages"],
                        "chunk_size_chars": len(doc_text),
                    }
                )

            export_data = {
                "export_metadata": {
                    "created_at": datetime.now().isoformat(),
                    "files_processed": 1,
                    "total_chunks": len(all_ids),
                    "chunk_size": args.chunk_size,
                    "overlap": args.overlap,
                    "optimized_for": "MedGemma (128k context)",
                    "mode": "simplified (filename as source, references removed)",
                },
                "ids": all_ids,
                "documents": all_documents,
                "metadatas": all_metadatas,
            }

            output_file = args.output
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                output_file = str(output_dir / f"medgemma_kb_{timestamp}.json")
            else:
                output_path = Path(output_file)
                if output_path.parent:
                    output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Processed 1 PDF → {len(result['chunks'])} chunks")
            print(f"✓ Source: {result['source']}")
            print(f"✓ Saved to: {output_file}")

    elif path.is_dir():
        # Directory of PDFs
        process_pdfs_to_json(
            str(path),
            args.output,
            args.chunk_size,
            args.overlap,
            verbose=not args.quiet,
        )

    else:
        print(f"Error: {path} is not a valid file or directory")
        exit(1)
