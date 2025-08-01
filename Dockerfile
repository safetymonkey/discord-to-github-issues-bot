# Multi-stage Dockerfile using uv for efficient dependency management
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies into a virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r pyproject.toml

# Production stage
FROM python:3.11-slim as production

# Install security updates and clean up in a single layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser -s /bin/false botuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/

# Create data directory for SQLite database with proper permissions
RUN mkdir -p /app/data && chown -R botuser:botuser /app/data

# Create application user's home directory
RUN mkdir -p /home/botuser && chown -R botuser:botuser /home/botuser

# Switch to non-root user
USER botuser

# Set environment variables
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/bot_data.db
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.db.database import health_check; exit(0 if health_check() else 1)"

# Expose no ports (bot doesn't serve HTTP)
# EXPOSE statement omitted as Discord bots don't need to expose ports

# Set labels for better container management
LABEL maintainer="discord-github-bot" \
      description="Discord bot that creates GitHub issues from Discord messages" \
      version="0.1.0"

# Run the bot
CMD ["python", "-m", "src.bot"]