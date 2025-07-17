# Docker Setup for Metadata Harmonisation Tool

This directory contains Docker configuration files for containerizing the Metadata Harmonisation Tool with multi-provider AI support.

## Files Overview

- `Dockerfile` - Multi-stage Docker build configuration
- `docker-compose.yml` - Base Docker Compose configuration
- `docker-compose.dev.yml` - Development-specific overrides
- `docker-compose.prod.yml` - Production-specific overrides
- `build.sh` / `build.bat` - Build scripts for different platforms
- `.dockerignore` - Files to exclude from Docker build context

## Quick Start

### 1. Build the Docker Image

**Linux/Mac:**
```bash
./docker/build.sh
```

**Windows:**
```cmd
docker\build.bat
```

**Manual build:**
```bash
docker build -f docker/Dockerfile -t metadata-harmonisation-tool:latest .
```

### 2. Run with Docker Compose

**Basic setup:**
```bash
docker-compose -f docker/docker-compose.yml up
```

**Development mode:**
```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

**Production mode:**
```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

### 3. Access the Application

- **Application**: http://localhost:8501
- **Health Check**: http://localhost:8501/_stcore/health

## Configuration

### Environment Variables

Create a `.env` file in the project root with your AI provider configurations:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### Volume Mounts

The Docker setup includes several volume mounts:

- `./input:/app/input:ro` - Input data (read-only)
- `./output:/app/output` - Output data (read-write)
- `./logs:/app/logs` - Application logs (read-write)

## Development Setup

### Hot Reload Development

For development with hot reload:

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

This setup:
- Mounts source code for live editing
- Enables Streamlit file watching
- Includes test files
- Disables restart policies for easier debugging

### Running Tests in Container

```bash
# Run core AI functionality tests
docker exec -it metadata-harmonisation-tool python test_ai_functionality.py

# Run integrated components tests
docker exec -it metadata-harmonisation-tool python test_integrated_components.py

# Run error handling tests
docker exec -it metadata-harmonisation-tool python test_error_handling.py
```

## Production Deployment

### Basic Production Setup

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

### With Ollama Service

```bash
docker-compose -f docker/docker-compose.yml --profile ollama up -d
```

### With Nginx Reverse Proxy

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --profile nginx up -d
```

### With Monitoring

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --profile monitoring up -d
```

## Profiles

The Docker Compose setup includes several profiles for optional services:

- `ollama` - Local Ollama AI service
- `nginx` - Reverse proxy with SSL support
- `monitoring` - Prometheus monitoring
- `database` - Development database (PostgreSQL)

## Security Features

### Container Security

- Non-root user execution (`appuser`)
- Minimal base image (python:3.11-slim)
- Multi-stage build to reduce attack surface
- Proper file permissions and ownership

### Network Security

- Isolated Docker network
- Health checks for service monitoring
- Configurable CORS and XSRF protection

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change port mapping in docker-compose.yml
2. **Permission issues**: Ensure proper file ownership
3. **Memory issues**: Adjust resource limits in production config
4. **AI provider connectivity**: Check network configuration and API keys

### Debugging

```bash
# View container logs
docker logs metadata-harmonisation-tool

# Access container shell
docker exec -it metadata-harmonisation-tool /bin/bash

# Check container health
docker inspect metadata-harmonisation-tool | grep Health -A 10
```

### Performance Tuning

For production deployments:

1. Adjust resource limits in `docker-compose.prod.yml`
2. Configure proper logging levels
3. Use external AI providers for better performance
4. Consider using a reverse proxy for SSL termination

## Maintenance

### Updating the Application

```bash
# Rebuild and restart
docker-compose down
docker build -f docker/Dockerfile -t metadata-harmonisation-tool:latest .
docker-compose up -d
```

### Backup and Restore

```bash
# Backup volumes
docker run --rm -v metadata-harmonisation-tool_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v metadata-harmonisation-tool_ollama_data:/data -v $(pwd):/backup alpine tar xzf /backup/ollama_backup.tar.gz -C /data
```

## Support

For issues and questions:
1. Check the main project README
2. Review Docker logs for error messages
3. Verify environment variable configuration
4. Test AI provider connectivity outside of Docker
