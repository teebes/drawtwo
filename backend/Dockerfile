# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        bash-completion \
        postgresql-client \
        build-essential \
        libpq-dev \
        less \
        procps \
        readline-common \
        vim-tiny \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create a non-root user with an interactive shell for docker-compose exec
RUN groupadd -r appuser && useradd -m -r -g appuser -s /bin/bash appuser

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Create entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Configure interactive shell niceties for docker-compose exec sessions
COPY docker-bashrc /home/appuser/.bashrc

# Change ownership of app directory to the non-root user
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
