"""
docparse — PDF extraction microservice powered by PyMuPDF.

Exposes PDF text extraction, table extraction, and image metadata
over a simple HTTP API.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import logging
import os
from contextlib import asynccontextmanager

import pymupdf
import uvicorn
from fastapi import APIRouter, FastAPI, File, Form, UploadFile, HTTPException

from app.models import (
    ExtractionResponse,
    TextExtractionResponse,
    TableExtractionResponse,
    HealthResponse,
)
from app.extraction import extract_full, extract_text_only, extract_tables_only
from app.version import __version__

log_level = os.getenv("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class _HealthCheckFilter(logging.Filter):
    """Suppress noisy health-check access-log lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/v1/health" not in msg


logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"docparse v{__version__} starting (PyMuPDF {pymupdf.VersionBind})")
    yield
    logger.info("docparse shutting down")


app = FastAPI(
    title="docparse",
    description="PDF extraction microservice powered by PyMuPDF. Licensed under AGPL-3.0.",
    version=__version__,
    lifespan=lifespan,
)


MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024  # default 50 MB

router = APIRouter(prefix="/v1")


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Read and validate an uploaded file."""
    filename = file.filename or "unknown.pdf"
    
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    if len(content) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb}MB",
        )
    
    return content, filename


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    file: UploadFile = File(...),
    extract_tables: bool = Form(default=True),
    extract_images: bool = Form(default=False),
    layout_mode: bool = Form(default=True),
    page_range: str = Form(default=None),
):
    """
    Full PDF extraction: text, tables, images, and scanned page detection.
    
    Upload a PDF file and receive structured extraction results including
    per-page text, detected tables (as markdown), image metadata, and
    scanned page detection.
    """
    content, filename = await _read_upload(file)
    
    logger.info(f"Full extraction: {filename} ({len(content)} bytes)")
    
    result = extract_full(
        file_bytes=content,
        filename=filename,
        extract_tables=extract_tables,
        extract_images=extract_images,
        layout_mode=layout_mode,
        page_range=page_range if page_range else None,
    )
    
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    
    logger.info(
        f"Extracted {filename}: {result.total_pages} pages, "
        f"{result.scanned_page_count} scanned, "
        f"{len(result.full_text)} chars"
    )
    
    return result


@router.post("/extract/text", response_model=TextExtractionResponse)
async def extract_text(
    file: UploadFile = File(...),
    layout_mode: bool = Form(default=True),
    page_range: str = Form(default=None),
):
    """
    Lightweight text-only extraction from a PDF.
    
    Faster than full extraction when you only need the text content.
    """
    content, filename = await _read_upload(file)
    
    logger.info(f"Text extraction: {filename} ({len(content)} bytes)")
    
    result = extract_text_only(
        file_bytes=content,
        filename=filename,
        layout_mode=layout_mode,
        page_range=page_range if page_range else None,
    )
    
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    
    return result


@router.post("/extract/tables", response_model=TableExtractionResponse)
async def extract_tables_endpoint(
    file: UploadFile = File(...),
    page_range: str = Form(default=None),
):
    """
    Extract only tables from a PDF.
    
    Returns detected tables as structured data and markdown format.
    """
    content, filename = await _read_upload(file)
    
    logger.info(f"Table extraction: {filename} ({len(content)} bytes)")
    
    result = extract_tables_only(
        file_bytes=content,
        filename=filename,
        page_range=page_range if page_range else None,
    )
    
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    
    return result


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
        pymupdf_version=pymupdf.VersionBind,
    )


app.include_router(router)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "12330"))
    workers = int(os.getenv("WORKERS", "1"))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        log_level=log_level.lower(),
    )
