# Use Python slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for tree-sitter
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone tree-sitter-ruby grammar (needed for parsing)
RUN git clone --depth 1 https://github.com/tree-sitter/tree-sitter-ruby /tree-sitter-ruby || true

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire ruby_agent package
# When building from ruby_agent directory, copy everything to maintain package structure
COPY . ./ruby_agent/

# Create directory for config and output
RUN mkdir -p /app/output /root/.ruby_agent

# Add /app to PYTHONPATH so Python can find the ruby_agent module
ENV PYTHONPATH=/app

# Expose the default server port
EXPOSE 8000

# Set default command to show help
CMD ["python", "-m", "ruby_agent.main", "--help"]
