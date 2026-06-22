FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including postgresql-client for pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wait-for-db script and make it executable
COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

# Copy requirements and install dependencies
COPY requirements.txt .
# Upgrade pip, setuptools and wheel to use prebuilt wheels when possible and reduce memory usage during builds
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Use wait-for-db script as entrypoint to ensure DB is ready
ENTRYPOINT ["/wait-for-db.sh"]

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
