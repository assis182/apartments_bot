FROM python:3.10-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
COPY run_worker.sh /app/run_worker.sh

# Create a directory for persistent storage and set permissions
RUN mkdir -p /app/data && \
    chmod 777 /app/data && \
    chmod +x /app/run_worker.sh

# Set container environment variable
ENV CONTAINER_ENV=true

# Add volume configuration
VOLUME ["/app/data"]

# Run the worker script
CMD ["/app/run_worker.sh"]