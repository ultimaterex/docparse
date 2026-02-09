"""
Request/response models for the docparse API.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExtractionOptions(BaseModel):
    """Options for PDF extraction."""
    extract_tables: bool = Field(default=True, description="Extract tables as structured markdown")
    extract_images: bool = Field(default=False, description="Extract image metadata from the PDF")
    layout_mode: bool = Field(default=True, description="Use layout-aware text extraction preserving spatial positioning")
    page_range: Optional[str] = Field(default=None, description="Page range to extract, e.g. '0-5' or '0,2,4'. None means all pages.")


class PageResult(BaseModel):
    """Extraction result for a single page."""
    page_number: int = Field(description="Zero-indexed page number")
    text: str = Field(description="Extracted text content")
    tables: list[dict] = Field(default_factory=list, description="Extracted tables as list of row-dicts")
    tables_markdown: list[str] = Field(default_factory=list, description="Extracted tables formatted as markdown")
    images: list[dict] = Field(default_factory=list, description="Image metadata (xref, size, colorspace)")
    is_scanned: bool = Field(default=False, description="Whether this page appears to be a scanned image with no extractable text")
    text_block_count: int = Field(default=0, description="Number of text blocks detected on the page")


class ExtractionResponse(BaseModel):
    """Full extraction response."""
    success: bool
    filename: str
    total_pages: int
    pages: list[PageResult]
    full_text: str = Field(description="Concatenated text from all pages")
    full_text_with_tables: str = Field(description="Concatenated text with tables inserted as markdown")
    scanned_page_count: int = Field(default=0, description="Number of pages detected as scanned/image-based")
    error: Optional[str] = None


class TextExtractionResponse(BaseModel):
    """Lightweight text-only response."""
    success: bool
    filename: str
    total_pages: int
    text: str
    scanned_page_count: int = Field(default=0)
    error: Optional[str] = None


class TableExtractionResponse(BaseModel):
    """Table-only extraction response."""
    success: bool
    filename: str
    total_pages: int
    tables: list[dict] = Field(description="All tables found across all pages, with page numbers")
    tables_markdown: list[str] = Field(description="All tables formatted as markdown")
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    pymupdf_version: str
