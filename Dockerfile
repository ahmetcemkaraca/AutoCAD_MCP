# AutoCAD MCP Server - Production Docker Image
FROM python:3.12-slim

# Metadata
LABEL maintainer="AutoCAD MCP Team"
LABEL description="AutoCAD MCP Server - AI-Powered Development Platform"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --user-group autocad_mcp

# Copy requirements files
COPY requirements.txt requirements-prod.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY *.md ./
COPY *.json ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/cache && \
    chown -R autocad_mcp:autocad_mcp /app

# Switch to non-root user
USER autocad_mcp

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV RATE_LIMITING_ENABLED=true
ENV SECURITY_SCANNING_ENABLED=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()"

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "src.mcp_integration.enhanced_mcp_server", "--host", "0.0.0.0", "--port", "8000"]