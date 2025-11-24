FROM node:18-bullseye

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create python symlink
RUN ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY requirements.txt .

# Install dependencies
RUN npm ci
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use shell form to handle PORT environment variable
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
