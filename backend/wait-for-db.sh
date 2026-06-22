#!/bin/sh
# wait-for-db.sh
# Waits for PostgreSQL to be ready before starting the application
# This prevents race conditions where the app starts before the database is accepting connections

set -e

# Get database configuration from environment variables
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-email_agent}"
DB_NAME="${DB_NAME:-email_agent_db}"

echo "🔍 Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# Retry logic
MAX_RETRIES=30
RETRY_COUNT=0
RETRY_INTERVAL=3

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    if [ $RETRY_COUNT -gt $MAX_RETRIES ]; then
        echo "❌ PostgreSQL failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    
    echo "⏳ PostgreSQL not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES), waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "✅ PostgreSQL is ready!"

# Optionally wait for Redis if configured
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

if [ -n "$REDIS_HOST" ]; then
    echo "🔍 Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
    
    RETRY_COUNT=0
    until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        
        if [ $RETRY_COUNT -gt 30 ]; then
            echo "⚠️ Redis failed to start, continuing anyway..."
            break
        fi
        
        echo "⏳ Redis not ready yet, waiting..."
        sleep 2
    done
    
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        echo "✅ Redis is ready!"
    fi
fi

echo "✅ All dependencies are ready, starting application..."

# Execute the main command
exec "$@"
