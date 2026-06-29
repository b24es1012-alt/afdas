# ─── AFDAS Backend Dockerfile ────────────────────────────────────────────────
# Multi-stage build for production deployment

# ═══ Stage 1: Builder ════════════════════════════════════════════════════════
FROM python:3.11-slim as builder

WORKDIR /app

# System dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ═══ Stage 2: Runtime ════════════════════════════════════════════════════════
FROM python:3.11-slim

WORKDIR /app

# Runtime geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    libgeos3.11.1 \
    libproj25 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create data directories
RUN mkdir -p /app/data/flood /app/data/osm /app/data/graphs

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -r afdas && chown -R afdas:afdas /app
USER afdas

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ping || exit 1

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
