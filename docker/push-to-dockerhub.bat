@echo off
REM Docker Hub Push Script for Metadata Harmonisation Tool (Windows)
REM Usage: push-to-dockerhub.bat [version]

setlocal enabledelayedexpansion

REM Default version if not provided
set VERSION=%1
if "%VERSION%"=="" set VERSION=latest

set IMAGE_NAME=atwine/metadata-harmonisation-tool

echo 🐳 Pushing Metadata Harmonisation Tool to Docker Hub...
echo Image: %IMAGE_NAME%:%VERSION%

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop.
    exit /b 1
)

REM Build the image with proper tags
echo 🔨 Building image...
docker build -f docker/Dockerfile -t %IMAGE_NAME%:%VERSION% -t %IMAGE_NAME%:latest .
if errorlevel 1 (
    echo ❌ Build failed!
    exit /b 1
)

REM Push to Docker Hub
echo 📤 Pushing to Docker Hub...
docker push %IMAGE_NAME%:%VERSION%
if errorlevel 1 (
    echo ❌ Push failed! Please make sure you're logged in: docker login
    exit /b 1
)

if not "%VERSION%"=="latest" (
    docker push %IMAGE_NAME%:latest
)

echo ✅ Successfully pushed %IMAGE_NAME%:%VERSION% to Docker Hub!
echo 🔗 Available at: https://hub.docker.com/r/atwine/metadata-harmonisation-tool

REM Show image info
echo.
echo 📊 Image Information:
docker images %IMAGE_NAME%

pause
