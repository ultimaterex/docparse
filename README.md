# docparse

A lightweight PDF extraction microservice powered by [PyMuPDF](https://pymupdf.readthedocs.io/). Exposes high-quality text extraction, table detection, and scanned page detection over a simple network API.

## Why

Most PDF text extraction libraries (like pypdf) produce garbled output — they lose layout, mangle tables, and can't detect scanned pages. PyMuPDF provides dramatically better extraction quality with layout-aware text, built-in table detection, and image metadata extraction.

docparse wraps PyMuPDF in a thin FastAPI service so it can be used as a sidecar container by any service that needs PDF processing.

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

The service will be available at `http://localhost:8800`. Visit `http://localhost:8800/docs` for the interactive API docs.

### Local

```bash
pip install -r requirements.txt
python -m app.main
```

## API

### `POST /extract` — Full extraction

Upload a PDF and get back text, tables, image metadata, and scanned page detection per page.

```bash
curl -X POST http://localhost:8800/extract \
  -F "file=@document.pdf" \
  -F "extract_tables=true" \
  -F "layout_mode=true"
```

**Form parameters:**
- `file` (required) — PDF file upload
- `extract_tables` (bool, default: `true`) — Extract tables as structured markdown
- `extract_images` (bool, default: `false`) — Extract image metadata
- `layout_mode` (bool, default: `true`) — Preserve spatial layout in text extraction
- `page_range` (string, optional) — Pages to extract, e.g. `"0-5"` or `"0,2,4"`

### `POST /extract/text` — Text only

Lightweight endpoint returning just the extracted text.

```bash
curl -X POST http://localhost:8800/extract/text \
  -F "file=@document.pdf"
```

### `POST /extract/tables` — Tables only

Extract only the detected tables as structured data and markdown.

```bash
curl -X POST http://localhost:8800/extract/tables \
  -F "file=@document.pdf"
```

### `GET /health` — Health check

```bash
curl http://localhost:8800/health
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8800` | Server port |
| `WORKERS` | `1` | Number of uvicorn workers |
| `LOG_LEVEL` | `info` | Logging level |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload file size in MB |

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0), as required by the PyMuPDF dependency.

**What this means:** If you modify this service and make it available over a network, you must make the modified source code available under the same license. Services that communicate with docparse over the network are **not** affected — only modifications to docparse itself.
