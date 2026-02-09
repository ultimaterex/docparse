"""
Startup banner display for docparse.

Shows a formatted splash screen on startup with version info,
configuration, and API endpoints.
"""

import os
from app.version import __version__


def display_startup_banner(port: int, workers: int):
    """
    Display a splash banner when docparse starts.

    Args:
        port: The port the server is listening on.
        workers: Number of worker processes.
    """
    host = "localhost"
    max_mb = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

    sep = "─" * 58

    art = r"""
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║               ┌─┐┌─┐┌─┐┌─┐┌─┐┬─┐┌─┐┌─┐               ║
    ║               │ ││ ││  │─┘├─┤├┬┘└─┐├┤                ║
    ║               └─┘└─┘└─┘┘  ┘ ┘┘└─└─┘└─┘               ║
    ║                                                      ║
    ║              PDF extraction microservice             ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝"""

    info_lines = [
        "",
        f"  ▸ Version      {__version__}",
        f"  ▸ Workers      {workers}",
        f"  ▸ Max Upload   {max_mb} MB",
        "",
        f"  {sep}",
        "",
        f"  ▸ API          http://{host}:{port}/v1",
        f"  ▸ Health       http://{host}:{port}/v1/health",
        f"  ▸ Docs         http://{host}:{port}/docs",
        "",
        f"  {sep}",
        "",
        "  Endpoints:",
        "    POST /v1/extract         Full extraction",
        "    POST /v1/extract/text    Text only",
        "    POST /v1/extract/tables  Tables only",
        "    GET  /v1/health          Health check",
        "",
        f"  {sep}",
        "  Ready to parse! 📄",
        "",
    ]

    print(art)
    for line in info_lines:
        print(line)
