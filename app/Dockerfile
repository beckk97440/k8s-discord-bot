# Base Image
FROM python:3.11-slim

# Metadata
LABEL maintainer="thomas.pretat@protonmail.com"
LABEL description="LoL Esports Discord Bot"
LABEL version="1.0.0"


WORKDIR /app

# Copy and Install Requirements/Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Create a non-root user and set permissions
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app


# Copy the application code
COPY --chown=botuser:botuser bot.py .


# Switch to the non-root user
USER botuser


# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"


CMD ["python", "-u", "bot.py"]