[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendRoot = Join-Path $repositoryRoot 'backend'
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$verificationRoot = Join-Path ([System.IO.Path]::GetTempPath()) "email-productivity-agent-verify-$PID"
$backendVenv = Join-Path $verificationRoot 'backend-venv'

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name (exit code $LASTEXITCODE)"
    }
}

try {
    New-Item -ItemType Directory -Path $verificationRoot -Force | Out-Null

    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pythonLauncher) {
        $pythonCommand = { py -3.11 @args }
    } else {
        $pythonCommand = { python3.11 @args }
    }

    Invoke-Step 'Check Python 3.11' {
        & $pythonCommand --version
        if ($LASTEXITCODE -ne 0) {
            throw 'Python 3.11 is required but was not found.'
        }
    }

    Invoke-Step 'Create backend verification environment' {
        & $pythonCommand -m venv $backendVenv
    }

    $backendPython = Join-Path $backendVenv 'Scripts\python.exe'
    if (-not (Test-Path $backendPython)) {
        $backendPython = Join-Path $backendVenv 'bin\python'
    }

    if (-not $SkipInstall) {
        Invoke-Step 'Install backend lockfile' {
            & $backendPython -m pip install --disable-pip-version-check --no-input -r (Join-Path $backendRoot 'requirements-lock.txt')
        }
    }

    Push-Location $backendRoot
    try {
        Invoke-Step 'Run backend tests' {
            & $backendPython -m pytest tests --cov=app --cov-report=term-missing
        }
        Invoke-Step 'Run backend Ruff lint' {
            & $backendPython -m ruff check .
        }
        Invoke-Step 'Check backend formatting' {
            & $backendPython -m ruff format --check .
        }
    } finally {
        Pop-Location
    }

    Push-Location $frontendRoot
    try {
        if (-not $SkipInstall) {
            Invoke-Step 'Install frontend lockfile' {
                npm ci
            }
        }
        Invoke-Step 'Run frontend tests' {
            npm test -- --run
        }
        Invoke-Step 'Run frontend lint' {
            npm run lint
        }
        Invoke-Step 'Check frontend formatting' {
            npm run format:check
        }
        Invoke-Step 'Run frontend typecheck' {
            npm run typecheck
        }
        Invoke-Step 'Build frontend' {
            npm run build
        }
    } finally {
        Pop-Location
    }

    Write-Host "`nFresh-clone verification passed." -ForegroundColor Green
} finally {
    if (Test-Path $verificationRoot) {
        Remove-Item -Recurse -Force $verificationRoot -ErrorAction SilentlyContinue
    }
}
