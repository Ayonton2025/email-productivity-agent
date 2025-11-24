FROM node:18-bullseye

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app

COPY package*.json ./
COPY requirements.txt ./

RUN npm ci
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE tells Railway: "This is a web service"
EXPOSE 8000

# Start FastAPI with Railway's injected port
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
