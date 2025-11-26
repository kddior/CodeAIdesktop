# -*- coding: utf-8 -*-
"""
PDF Text Extraction Module
5 extraction methods + OCR fallback for maximum compatibility
"""

import logging
from pathlib import Path
from typing import Optional, List
import re

logger = logging.getLogger(__name__)


def extract_with_pymupdf(pdf_path: str) -> Optional[str]:
    """
    Method 1: Extract text using PyMuPDF (fitz)
    Fastest method, good for most PDFs
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text)

        doc.close()

        result = "\n\n".join(text_parts)
        logger.info(f"PyMuPDF extracted {len(result)} chars from {len(text_parts)} pages")
        return result if result.strip() else None

    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed")
        return None
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        return None


def extract_with_pdfplumber(pdf_path: str) -> Optional[str]:
    """
    Method 2: Extract text using pdfplumber
    Better for tables and complex layouts
    """
    try:
        import pdfplumber

        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)

        result = "\n\n".join(text_parts)
        logger.info(f"pdfplumber extracted {len(result)} chars from {len(text_parts)} pages")
        return result if result.strip() else None

    except ImportError:
        logger.warning("pdfplumber not installed")
        return None
    except Exception as e:
        logger.error(f"pdfplumber extraction failed: {e}")
        return None


def extract_with_pypdf2(pdf_path: str) -> Optional[str]:
    """
    Method 3: Extract text using PyPDF2
    Reliable for standard PDFs
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text)

        result = "\n\n".join(text_parts)
        logger.info(f"PyPDF2 extracted {len(result)} chars from {len(text_parts)} pages")
        return result if result.strip() else None

    except ImportError:
        logger.warning("PyPDF2 not installed")
        return None
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
        return None


def extract_with_pypdf(pdf_path: str) -> Optional[str]:
    """
    Method 4: Extract text using pypdf (modern PyPDF2 successor)
    Modern alternative to PyPDF2
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text)

        result = "\n\n".join(text_parts)
        logger.info(f"pypdf extracted {len(result)} chars from {len(text_parts)} pages")
        return result if result.strip() else None

    except ImportError:
        logger.warning("pypdf not installed")
        return None
    except Exception as e:
        logger.error(f"pypdf extraction failed: {e}")
        return None


def extract_with_ocr(pdf_path: str, language: str = 'fra') -> Optional[str]:
    """
    Method 5: Extract text using OCR (Tesseract)
    Fallback for scanned documents or images
    Requires: sudo apt-get install tesseract-ocr tesseract-ocr-fra
    """
    try:
        import pytesseract
        from PIL import Image
        import fitz  # PyMuPDF for converting PDF to images

        logger.info(f"Starting OCR extraction with language={language}")

        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            # Convert PDF page to image
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Perform OCR
            text = pytesseract.image_to_string(img, lang=language)

            if text and text.strip():
                text_parts.append(text)

            logger.info(f"OCR page {page_num + 1}/{len(doc)}: {len(text)} chars")

        doc.close()

        result = "\n\n".join(text_parts)
        logger.info(f"OCR extracted {len(result)} chars from {len(text_parts)} pages")
        return result if result.strip() else None

    except ImportError as e:
        logger.warning(f"OCR dependencies not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None


def clean_extracted_text(text: str) -> str:
    """
    Clean and normalize extracted text
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    # Remove page numbers (common patterns)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    text = re.sub(r'\nPage \d+\n', '\n', text, flags=re.IGNORECASE)

    # Remove header/footer artifacts
    text = re.sub(r'\n_{3,}\n', '\n', text)
    text = re.sub(r'\n={3,}\n', '\n', text)

    return text.strip()


def extract_pdf_text(pdf_path: str, prefer_ocr: bool = False) -> str:
    """
    Extract text from PDF using the best available method
    Tries multiple methods in order until one succeeds

    Args:
        pdf_path: Path to PDF file
        prefer_ocr: If True, try OCR first (for scanned documents)

    Returns:
        Extracted text or empty string if all methods fail
    """
    pdf_path = str(Path(pdf_path).resolve())

    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return ""

    logger.info(f"Starting PDF extraction: {pdf_path}")

    # Define extraction order
    if prefer_ocr:
        methods = [
            ("OCR", extract_with_ocr),
            ("PyMuPDF", extract_with_pymupdf),
            ("pdfplumber", extract_with_pdfplumber),
            ("pypdf", extract_with_pypdf),
            ("PyPDF2", extract_with_pypdf2),
        ]
    else:
        methods = [
            ("PyMuPDF", extract_with_pymupdf),
            ("pdfplumber", extract_with_pdfplumber),
            ("pypdf", extract_with_pypdf),
            ("PyPDF2", extract_with_pypdf2),
            ("OCR", extract_with_ocr),
        ]

    best_result = ""
    best_length = 0

    for method_name, method_func in methods:
        logger.info(f"Trying extraction method: {method_name}")

        try:
            result = method_func(pdf_path)

            if result and len(result) > best_length:
                best_result = result
                best_length = len(result)
                logger.info(f"{method_name} produced best result so far: {best_length} chars")

                # If we got a good result (>500 chars), we can stop trying
                if best_length > 500:
                    logger.info(f"Using {method_name} result ({best_length} chars)")
                    break

        except Exception as e:
            logger.error(f"{method_name} failed: {e}")
            continue

    if not best_result:
        logger.error("All extraction methods failed")
        return ""

    # Clean the text
    cleaned_text = clean_extracted_text(best_result)

    logger.info(f"Final extracted text: {len(cleaned_text)} chars (cleaned from {best_length})")

    return cleaned_text


def chunk_text_for_analysis(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks for LLM analysis
    Uses overlap to avoid losing context at boundaries

    Args:
        text: Text to chunk
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending in the last 200 chars of chunk
            last_period = text[end-200:end].rfind('.')
            if last_period != -1:
                end = end - 200 + last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap

    logger.info(f"Split text into {len(chunks)} chunks (avg {sum(len(c) for c in chunks) / len(chunks):.0f} chars)")

    return chunks


def get_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract PDF metadata (title, author, etc.)
    """
    try:
        import fitz

        doc = fitz.open(pdf_path)
        metadata = doc.metadata

        result = {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'page_count': len(doc)
        }

        doc.close()

        return result

    except Exception as e:
        logger.error(f"Failed to extract metadata: {e}")
        return {}


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_file_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"Testing PDF Extraction: {pdf_path}")
    print(f"{'='*60}\n")

    # Get metadata
    print("Metadata:")
    metadata = get_pdf_metadata(pdf_path)
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    print(f"\n{'='*60}\n")

    # Extract text
    text = extract_pdf_text(pdf_path)

    if text:
        print(f"Extraction successful!")
        print(f"Total length: {len(text)} characters")
        print(f"\nFirst 500 characters:")
        print("-" * 60)
        print(text[:500])
        print("-" * 60)

        # Chunk the text
        chunks = chunk_text_for_analysis(text, chunk_size=2000)
        print(f"\nChunked into {len(chunks)} parts")
        print(f"Chunk sizes: {[len(c) for c in chunks]}")

    else:
        print("Extraction failed!")
        sys.exit(1)
