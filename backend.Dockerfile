# ==========================================
# OceanIQ Backend - FastAPI Dockerfile 
# ==========================================
FROM python:3.10-slim

# System setup packages for GIS/Scipy compiles if wheels fail
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libgdal-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --default-timeout=120 --retries 10 --no-cache-dir -r requirements.txt

# Install CPU-only PyTorch separately (with timeout resilience)
RUN pip install --default-timeout=120 --retries 10 --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.2+cpu

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Command to boot the FastAPI directly
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
