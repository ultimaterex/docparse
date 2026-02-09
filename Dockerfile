FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

EXPOSE 8800

ENV PORT=8800
ENV WORKERS=1
ENV LOG_LEVEL=info
ENV MAX_FILE_SIZE_MB=50

CMD ["python", "-m", "app.main"]
