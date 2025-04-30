FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /app/
COPY poetry.lock poetry.toml pyproject.toml /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install web-search-agent package
RUN pip install --no-cache-dir web-search-agent

# Copy application code
COPY . /app/

# Create output directory if it doesn't exist
RUN mkdir -p /app/src/output

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.main"]