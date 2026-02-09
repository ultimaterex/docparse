"""
PDF extraction logic using PyMuPDF.

This module provides the core extraction functionality:
- Layout-aware text extraction
- Table detection and extraction
- Image metadata extraction
- Scanned/image-based page detection
"""

import io
import logging
from typing import Optional

import pymupdf

from app.models import PageResult, ExtractionResponse, TextExtractionResponse, TableExtractionResponse

logger = logging.getLogger(__name__)


def parse_page_range(page_range: Optional[str], total_pages: int) -> list[int]:
    """
    Parse a page range string into a list of page indices.
    
    Supports formats like:
    - "0-5" -> [0, 1, 2, 3, 4, 5]
    - "0,2,4" -> [0, 2, 4]
    - "0-2,5,7-9" -> [0, 1, 2, 5, 7, 8, 9]
    - None -> all pages
    """
    if page_range is None:
        return list(range(total_pages))
    
    pages = set()
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(0, int(start.strip()))
            end = min(total_pages - 1, int(end.strip()))
            pages.update(range(start, end + 1))
        else:
            page_num = int(part.strip())
            if 0 <= page_num < total_pages:
                pages.add(page_num)
    
    return sorted(pages)


def _detect_scanned_page(page: pymupdf.Page, text: str) -> bool:
    """
    Detect if a page is scanned/image-based.
    
    A page is considered scanned if it has images but very little
    or no extractable text.
    """
    images = page.get_images(full=False)
    text_stripped = text.strip()
    
    # Page has images but minimal text (< 20 chars could be artifacts)
    if len(images) > 0 and len(text_stripped) < 20:
        return True
    
    return False


def _extract_page_text(page: pymupdf.Page, layout_mode: bool) -> str:
    """Extract text from a single page."""
    if layout_mode:
        # "text" with sort=True preserves reading order
        # Using flags for better extraction
        text = page.get_text(
            "text",
            sort=True,
            flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_DEHYPHENATE
        )
    else:
        text = page.get_text("text")
    
    return text


def _extract_page_tables(page: pymupdf.Page) -> tuple[list[dict], list[str]]:
    """
    Extract tables from a page using PyMuPDF's table finder.
    
    Returns:
        Tuple of (tables_as_dicts, tables_as_markdown)
    """
    tables_data = []
    tables_markdown = []
    
    try:
        tables = page.find_tables()
        
        for i, table in enumerate(tables):
            # Extract as list of lists
            extracted = table.extract()
            if not extracted or len(extracted) == 0:
                continue
            
            # Build dict representation
            table_dict = {
                "table_index": i,
                "bbox": list(table.bbox),
                "rows": len(extracted),
                "cols": len(extracted[0]) if extracted else 0,
                "data": extracted,
            }
            tables_data.append(table_dict)
            
            # Build markdown representation
            md = _table_to_markdown(extracted)
            if md:
                tables_markdown.append(md)
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")
    
    return tables_data, tables_markdown


def _table_to_markdown(data: list[list]) -> str:
    """Convert a table (list of lists) to markdown format."""
    if not data or len(data) == 0:
        return ""
    
    # Clean cell values
    rows = []
    for row in data:
        cleaned = []
        for cell in row:
            val = str(cell) if cell is not None else ""
            # Replace newlines within cells
            val = val.replace("\n", " ").strip()
            cleaned.append(val)
        rows.append(cleaned)
    
    if len(rows) == 0:
        return ""
    
    # Determine column widths for alignment
    num_cols = max(len(row) for row in rows)
    
    # Pad rows to have equal columns
    for row in rows:
        while len(row) < num_cols:
            row.append("")
    
    # Build markdown table
    lines = []
    
    # Header row
    lines.append("| " + " | ".join(rows[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    # Data rows
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def _extract_page_images(page: pymupdf.Page) -> list[dict]:
    """Extract image metadata from a page."""
    images = []
    
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        width = img[2]
        height = img[3]
        colorspace = img[5]
        
        images.append({
            "index": img_index,
            "xref": xref,
            "width": width,
            "height": height,
            "colorspace": colorspace,
        })
    
    return images


def extract_full(
    file_bytes: bytes,
    filename: str,
    extract_tables: bool = True,
    extract_images: bool = False,
    layout_mode: bool = True,
    page_range: Optional[str] = None,
) -> ExtractionResponse:
    """
    Full extraction: text, tables, images, and scanned detection.
    """
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return ExtractionResponse(
            success=False,
            filename=filename,
            total_pages=0,
            pages=[],
            full_text="",
            full_text_with_tables="",
            error=f"Failed to open PDF: {str(e)}",
        )
    
    try:
        total_pages = len(doc)
        page_indices = parse_page_range(page_range, total_pages)
        
        pages = []
        all_text_parts = []
        all_text_with_tables_parts = []
        scanned_count = 0
        
        for page_num in page_indices:
            page = doc[page_num]
            
            # Extract text
            text = _extract_page_text(page, layout_mode)
            
            # Detect scanned
            is_scanned = _detect_scanned_page(page, text)
            if is_scanned:
                scanned_count += 1
            
            # Count text blocks
            blocks = page.get_text("blocks")
            text_block_count = len([b for b in blocks if b[6] == 0])  # type 0 = text
            
            # Extract tables
            tables_data = []
            tables_md = []
            if extract_tables:
                tables_data, tables_md = _extract_page_tables(page)
            
            # Extract images
            image_meta = []
            if extract_images:
                image_meta = _extract_page_images(page)
            
            page_result = PageResult(
                page_number=page_num,
                text=text,
                tables=tables_data,
                tables_markdown=tables_md,
                images=image_meta,
                is_scanned=is_scanned,
                text_block_count=text_block_count,
            )
            pages.append(page_result)
            
            # Build concatenated text
            all_text_parts.append(text)
            
            # Build text with tables inserted
            page_text_with_tables = text
            if tables_md:
                page_text_with_tables += "\n\n" + "\n\n".join(tables_md)
            all_text_with_tables_parts.append(page_text_with_tables)
        
        full_text = "\n".join(all_text_parts).strip()
        full_text_with_tables = "\n".join(all_text_with_tables_parts).strip()
        
        return ExtractionResponse(
            success=True,
            filename=filename,
            total_pages=total_pages,
            pages=pages,
            full_text=full_text,
            full_text_with_tables=full_text_with_tables,
            scanned_page_count=scanned_count,
        )
    finally:
        doc.close()


def extract_text_only(
    file_bytes: bytes,
    filename: str,
    layout_mode: bool = True,
    page_range: Optional[str] = None,
) -> TextExtractionResponse:
    """Lightweight text-only extraction."""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return TextExtractionResponse(
            success=False,
            filename=filename,
            total_pages=0,
            text="",
            error=f"Failed to open PDF: {str(e)}",
        )
    
    try:
        total_pages = len(doc)
        page_indices = parse_page_range(page_range, total_pages)
        
        text_parts = []
        scanned_count = 0
        
        for page_num in page_indices:
            page = doc[page_num]
            text = _extract_page_text(page, layout_mode)
            text_parts.append(text)
            
            if _detect_scanned_page(page, text):
                scanned_count += 1
        
        return TextExtractionResponse(
            success=True,
            filename=filename,
            total_pages=total_pages,
            text="\n".join(text_parts).strip(),
            scanned_page_count=scanned_count,
        )
    finally:
        doc.close()


def extract_tables_only(
    file_bytes: bytes,
    filename: str,
    page_range: Optional[str] = None,
) -> TableExtractionResponse:
    """Table-only extraction."""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return TableExtractionResponse(
            success=False,
            filename=filename,
            total_pages=0,
            tables=[],
            tables_markdown=[],
            error=f"Failed to open PDF: {str(e)}",
        )
    
    try:
        total_pages = len(doc)
        page_indices = parse_page_range(page_range, total_pages)
        
        all_tables = []
        all_markdown = []
        
        for page_num in page_indices:
            page = doc[page_num]
            tables_data, tables_md = _extract_page_tables(page)
            
            for table in tables_data:
                table["page_number"] = page_num
                all_tables.append(table)
            
            all_markdown.extend(tables_md)
        
        return TableExtractionResponse(
            success=True,
            filename=filename,
            total_pages=total_pages,
            tables=all_tables,
            tables_markdown=all_markdown,
        )
    finally:
        doc.close()
