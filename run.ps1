# Usage: .\run.ps1 [command]
# Commands: dev, run, format, lint, lint-fix, check, docker-up, docker-build, docker-down, docker-logs

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Load .env.local into current session
function Load-EnvLocal {
    if (Test-Path ".env.local") {
        Get-Content ".env.local" | ForEach-Object {
            if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
                $key   = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                Write-Host "  SET $key=$value" -ForegroundColor DarkGray
            }
        }
        Write-Host ""
    } else {
        Write-Warning ".env.local not found. Copy .env.example to .env.local and fill in values."
        exit 1
    }
}

switch ($Command) {

    "dev" {
        Write-Host "Starting dev server with hot reload..." -ForegroundColor Green
        Load-EnvLocal
        uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
    }

    "run" {
        Write-Host "Starting server..." -ForegroundColor Green
        Load-EnvLocal
        uvicorn app.main:app --host 0.0.0.0 --port 9000
    }

    "format" {
        Write-Host "Formatting code with ruff..." -ForegroundColor Cyan
        ruff format app/
    }

    "lint" {
        Write-Host "Checking lint..." -ForegroundColor Cyan
        ruff check app/
    }

    "lint-fix" {
        Write-Host "Auto-fixing lint issues..." -ForegroundColor Cyan
        ruff check app/ --fix
    }

    "check" {
        Write-Host "Running format + lint checks..." -ForegroundColor Cyan
        ruff format app/ --check
        ruff check app/
    }

    "docker-up" {
        Write-Host "Starting Docker containers..." -ForegroundColor Green
        docker compose up -d
    }

    "docker-build" {
        Write-Host "Building and starting Docker containers..." -ForegroundColor Green
        docker compose up -d --build
    }

    "docker-down" {
        Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
        docker compose down
    }

    "docker-logs" {
        Write-Host "Tailing container logs..." -ForegroundColor Cyan
        docker compose logs -f chroma-wrapper
    }

    default {
        Write-Host ""
        Write-Host "Usage: .\run.ps1 [command]" -ForegroundColor White
        Write-Host ""
        Write-Host "Available commands:" -ForegroundColor Yellow
        Write-Host "  dev           Run locally with hot reload"
        Write-Host "  run           Run locally without hot reload"
        Write-Host "  format        Format code with ruff"
        Write-Host "  lint          Check lint issues"
        Write-Host "  lint-fix      Auto-fix lint issues"
        Write-Host "  check         Run format + lint checks"
        Write-Host "  docker-up     Start Docker containers"
        Write-Host "  docker-build  Build and start Docker containers"
        Write-Host "  docker-down   Stop Docker containers"
        Write-Host "  docker-logs   Tail container logs"
        Write-Host ""
    }
}
