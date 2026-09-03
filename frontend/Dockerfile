FROM node:24-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies and tools required for healthchecks
RUN apk add --no-cache curl && npm ci --silent

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Default command for development
CMD ["npm", "run", "dev"]
