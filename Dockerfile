# FlushBot - Telegram Security Bot
# Multi-stage Docker build for production deployment

# Stage 1: Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage
FROM python:3.12-slim

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash flushbot

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/flushbot/.local

# Copy application code
COPY --chown=flushbot:flushbot . .

# Create required directories
RUN mkdir -p /app/data/exports/delayed_sweeps \
    /app/logs \
    && chown -R flushbot:flushbot /app/data /app/logs

# Set PATH to include user packages
ENV PATH=/home/flushbot/.local/bin:$PATH

# Switch to non-root user
USER flushbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Expose port (if needed for webhooks)
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]