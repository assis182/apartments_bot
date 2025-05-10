FROM python:3.10-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for persistent storage
RUN mkdir -p /app/data

# Run the script
CMD ["python", "-m", "src.main"]