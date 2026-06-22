# Dev helper: bring up services in correct order and run DB init
# Usage: Run from repo root in PowerShell (Windows)

param(
    [int]$PostgresReadyTimeoutSec = 120
)

Write-Host "Stopping existing stack and removing volumes (if any)..." -ForegroundColor Cyan
docker compose down -v

Write-Host "Building llama, backend, celery_worker, celery_beat images (no cache)..." -ForegroundColor Cyan
docker compose build --no-cache llama backend celery_worker celery_beat

Write-Host "Starting core infra: postgres and redis..." -ForegroundColor Cyan
docker compose up -d postgres redis

Write-Host "Waiting for Postgres to be healthy (timeout ${PostgresReadyTimeoutSec}s)..." -ForegroundColor Cyan
$start = Get-Date
while (((Get-Date) - $start).TotalSeconds -lt $PostgresReadyTimeoutSec) {
    # Use pg_isready via docker exec to check readiness
    try {
        $status = docker compose exec -T postgres pg_isready -U email_agent -d email_agent_db 2>&1
        if ($status -match "accepting connections") {
            Write-Host "Postgres ready" -ForegroundColor Green
            break
        }
    } catch {
        # ignore and retry
    }
    Start-Sleep -Seconds 2
}

if (((Get-Date) - $start).TotalSeconds -ge $PostgresReadyTimeoutSec) {
    Write-Host "Timed out waiting for Postgres to be ready." -ForegroundColor Yellow
    Write-Host "Check 'docker compose logs postgres' for details." -ForegroundColor Yellow
    exit 1
}

Write-Host "DB initialization is now handled automatically by docker-compose via the 'init_db' service; no manual run required." -ForegroundColor Cyan

Write-Host "Bringing up remaining services..." -ForegroundColor Cyan
docker compose up -d

Write-Host "Stack should be up. Check services with: docker compose ps" -ForegroundColor Green
Write-Host "Follow logs with: docker compose logs -f backend celery_beat" -ForegroundColor Green
