FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    grep \
    coreutils \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY media_bot.py .
COPY webhook_server.py .
COPY .env .

# Create logs directory
RUN mkdir -p logs

# Expose webhook port
EXPOSE 9999

# Run bot
CMD ["python3", "media_bot.py"]
