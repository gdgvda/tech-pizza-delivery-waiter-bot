# Dockerfile

# 1. Base Image: Use a specific Python version
FROM python:3.12-slim

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set Working Directory
WORKDIR /app

# 4. Install System Dependencies (Likely NONE needed for this simpler bot)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*
# We removed matplotlib, so the complex build dependencies are gone.

# 5. Install Python Dependencies
COPY requirements.txt .
# Ensure pip is up-to-date and install requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy Application Code
COPY . .

# 7. Create a non-root user and switch to it (Good Practice)
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# 8. Command to Run the Application
CMD ["python", "main.py"]