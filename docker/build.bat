@echo off
REM Build script for Metadata Harmonisation Tool Docker image (Windows)

setlocal enabledelayedexpansion

REM Configuration
set IMAGE_NAME=metadata-harmonisation-tool
set IMAGE_TAG=latest
set DOCKERFILE_PATH=docker/Dockerfile

echo Building Metadata Harmonisation Tool Docker image...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Build the Docker image
echo Building image: %IMAGE_NAME%:%IMAGE_TAG%
docker build -f %DOCKERFILE_PATH% -t %IMAGE_NAME%:%IMAGE_TAG% .

if errorlevel 0 (
    echo ✅ Docker image built successfully!
    echo Image: %IMAGE_NAME%:%IMAGE_TAG%
    
    REM Show image size
    echo Image size:
    docker images %IMAGE_NAME%:%IMAGE_TAG% --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    
    echo.
    echo To run the container:
    echo docker run -p 8501:8501 %IMAGE_NAME%:%IMAGE_TAG%
    
) else (
    echo ❌ Docker build failed!
    exit /b 1
)

pause
