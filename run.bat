@echo off
REM Usage: run.bat [command]
REM Commands: dev, run, format, lint, lint-fix, check, docker-up, docker-build, docker-down, docker-logs

SET CMD=%1

IF "%CMD%"=="dev" (
    FOR /F "tokens=*" %%i IN (.env.local) DO SET %%i
    uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
    GOTO end
)

IF "%CMD%"=="run" (
    FOR /F "tokens=*" %%i IN (.env.local) DO SET %%i
    uvicorn app.main:app --host 0.0.0.0 --port 9000
    GOTO end
)

IF "%CMD%"=="format" (
    ruff format app/
    GOTO end
)

IF "%CMD%"=="lint" (
    ruff check app/
    GOTO end
)

IF "%CMD%"=="lint-fix" (
    ruff check app/ --fix
    GOTO end
)

IF "%CMD%"=="check" (
    ruff format app/ --check
    ruff check app/
    GOTO end
)

IF "%CMD%"=="docker-up" (
    docker compose up -d
    GOTO end
)

IF "%CMD%"=="docker-build" (
    docker compose up -d --build
    GOTO end
)

IF "%CMD%"=="docker-down" (
    docker compose down
    GOTO end
)

IF "%CMD%"=="docker-logs" (
    docker compose logs -f chroma-wrapper
    GOTO end
)

echo Usage: run.bat [command]
echo.
echo Available commands:
echo   dev           Run locally with hot reload
echo   run           Run locally without hot reload
echo   format        Format code with ruff
echo   lint          Check lint issues
echo   lint-fix      Auto-fix lint issues
echo   check         Run format + lint checks
echo   docker-up     Start Docker containers
echo   docker-build  Build and start Docker containers
echo   docker-down   Stop Docker containers
echo   docker-logs   Tail container logs

:end
