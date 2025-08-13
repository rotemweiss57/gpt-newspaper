FROM python:3.11-slim as base

# Install system dependencies for Python packages and git
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with pinned versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY . .

# Create outputs directory and set permissions
RUN mkdir -p outputs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Make ports configurable via environment variables
ENV FRONTEND_PORT=5000
ENV BACKEND_PORT=8000

# Expose both ports
EXPOSE $FRONTEND_PORT $BACKEND_PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$FRONTEND_PORT/ || exit 1

# Run the application
CMD ["python", "app.py"]