#!/bin/bash
# Build script for Metadata Harmonisation Tool Docker image

set -e

# Configuration
IMAGE_NAME="metadata-harmonisation-tool"
IMAGE_TAG="latest"
DOCKERFILE_PATH="docker/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Metadata Harmonisation Tool Docker image...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Build the Docker image
echo -e "${YELLOW}Building image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
docker build -f ${DOCKERFILE_PATH} -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    echo -e "${GREEN}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    
    # Show image size
    echo -e "${YELLOW}Image size:${NC}"
    docker images ${IMAGE_NAME}:${IMAGE_TAG} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    
    echo -e "${GREEN}To run the container:${NC}"
    echo -e "${YELLOW}docker run -p 8501:8501 ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi
