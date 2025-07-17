#!/bin/bash

# Docker Hub Push Script for Metadata Harmonisation Tool
# Usage: ./push-to-dockerhub.sh [version]

set -e

# Default version if not provided
VERSION=${1:-latest}
IMAGE_NAME="atwine/metadata-harmonisation-tool"

echo "🐳 Pushing Metadata Harmonisation Tool to Docker Hub..."
echo "Image: ${IMAGE_NAME}:${VERSION}"

# Check if user is logged in to Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Please login to Docker Hub first:"
    echo "   docker login"
    exit 1
fi

# Build the image with proper tags
echo "🔨 Building image..."
docker build -f docker/Dockerfile -t ${IMAGE_NAME}:${VERSION} -t ${IMAGE_NAME}:latest .

# Push to Docker Hub
echo "📤 Pushing to Docker Hub..."
docker push ${IMAGE_NAME}:${VERSION}

if [ "${VERSION}" != "latest" ]; then
    docker push ${IMAGE_NAME}:latest
fi

echo "✅ Successfully pushed ${IMAGE_NAME}:${VERSION} to Docker Hub!"
echo "🔗 Available at: https://hub.docker.com/r/atwine/metadata-harmonisation-tool"

# Show image info
echo ""
echo "📊 Image Information:"
docker images ${IMAGE_NAME}
