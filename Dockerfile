FROM python:3.12-slim

ARG VERSION=unknown
LABEL version=$VERSION

# Install uv for faster package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY app/ app/

ENV PYTHONUNBUFFERED=1 APP_VERSION=$VERSION
ENV PORT=8800
ENV WORKERS=1
ENV LOG_LEVEL=info
ENV MAX_FILE_SIZE_MB=50

EXPOSE 8800

CMD ["python", "-m", "app.main"]
