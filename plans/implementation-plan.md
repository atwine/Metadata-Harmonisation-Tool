# Metadata Harmonisation Tool Enhancement - Implementation Plan

## Project Overview

**Goal**: Enhance the existing Metadata Harmonisation Tool to support multiple AI providers (Ollama, OpenAI, Anthropic, Azure OpenAI) with flexible model selection and containerize it with Docker for easy deployment.

**Current State**: Streamlit-based tool that uses only Ollama for AI functionality, with variable mapping, description generation, and transformation capabilities.

**Target State**: Multi-provider AI support with Docker containerization while maintaining all existing functionality.

## Architecture Overview

### System Components
1. **Configuration Layer**: Multi-provider AI configuration with validation
2. **AI Abstraction Layer**: Provider-agnostic interface for chat and embeddings
3. **Streamlit UI**: Enhanced with provider selection and configuration
4. **Docker Container**: Multi-stage build with environment flexibility
5. **Existing Components**: Preserved functionality for variable mapping and transformations

### File Structure Changes
```
Metadata-Harmonisation-Tool/
├── config.py                    # New: Multi-provider AI configuration
├── app/
│   ├── components/
│   │   ├── ai_config_ui.py     # New: Configuration UI component
│   │   ├── ai_provider.py      # New: Provider abstraction layer
│   │   └── util.py             # Modified: Updated to use new config
├── docker/
│   ├── Dockerfile              # New: Multi-stage Docker build
│   ├── docker-compose.yml      # New: Development setup
│   └── .dockerignore           # New: Docker ignore patterns
├── requirements.txt            # Updated: New dependencies
├── environment.yml             # Updated: New conda dependencies
├── .env.example               # New: Environment template
└── README.md                  # Updated: Multi-provider setup instructions
```

## Implementation Plan

### Phase 1: Core Infrastructure (Tasks 1-6)

#### Task 1: Create Multi-Provider Configuration System
**File**: `config.py`
**Estimated Time**: 2 hours
**Dependencies**: None

**Implementation Steps**:
1. Create `ModelConfig` class with provider enumeration
2. Implement environment variable loading
3. Add Streamlit session state integration
4. Create client initialization for each provider
5. Add model validation methods
6. Implement unified chat and embedding interfaces

**Acceptance Criteria**:
- [ ] Supports Ollama, OpenAI, Anthropic, Azure OpenAI providers
- [ ] Loads configuration from environment variables
- [ ] Validates API keys and model availability
- [ ] Provides unified interface for chat and embeddings
- [ ] Handles provider-specific message formats

#### Task 2: Create AI Provider Abstraction Layer
**File**: `app/components/ai_provider.py`
**Estimated Time**: 1.5 hours
**Dependencies**: Task 1

**Implementation Steps**:
1. Create `AIProvider` class that wraps `ModelConfig`
2. Implement provider-specific error handling
3. Add retry logic for API calls
4. Create embedding batch processing
5. Add response format normalization

**Acceptance Criteria**:
- [ ] Abstracts provider differences from application code
- [ ] Handles rate limiting and retries
- [ ] Normalizes responses across providers
- [ ] Provides clear error messages

#### Task 3: Create Configuration UI Component
**File**: `app/components/ai_config_ui.py`
**Estimated Time**: 2 hours
**Dependencies**: Task 1

**Implementation Steps**:
1. Create Streamlit sidebar configuration interface
2. Add provider selection dropdown
3. Implement API key input fields (masked)
4. Add model selection dropdowns
5. Create connection test functionality
6. Add configuration persistence

**Acceptance Criteria**:
- [ ] Intuitive provider selection interface
- [ ] Secure API key input (masked)
- [ ] Real-time connection validation
- [ ] Configuration persists across sessions
- [ ] Clear error messages for invalid configurations

#### Task 4: Update Existing Utility Functions
**File**: `app/components/util.py`
**Estimated Time**: 1 hour
**Dependencies**: Task 1, Task 2

**Implementation Steps**:
1. Replace direct Ollama client usage with `AIProvider`
2. Update `get_ollama_client()` to `get_ai_provider()`
3. Maintain backward compatibility where possible
4. Update error handling

**Acceptance Criteria**:
- [ ] All existing functionality works with new provider system
- [ ] No breaking changes to existing interfaces
- [ ] Improved error handling and user feedback

#### Task 5: Update Description Generation
**File**: `app/components/generate_descriptions.py`
**Estimated Time**: 1 hour
**Dependencies**: Task 2, Task 4

**Implementation Steps**:
1. Replace Ollama-specific calls with provider abstraction
2. Update embedding generation to use new interface
3. Ensure chat completion works across providers
4. Update error handling

**Acceptance Criteria**:
- [ ] Description generation works with all providers
- [ ] Embedding functionality preserved
- [ ] Error handling improved

#### Task 6: Update Recommendation System
**File**: `app/components/get_recommendations.py`
**Estimated Time**: 1 hour
**Dependencies**: Task 2, Task 4

**Implementation Steps**:
1. Update to use new AI provider interface
2. Ensure similarity matching works across providers
3. Update chat completion calls
4. Improve error handling

**Acceptance Criteria**:
- [ ] Recommendations work with all providers
- [ ] Similarity matching preserved
- [ ] Performance maintained

### Phase 2: User Interface Integration (Tasks 7-9)

#### Task 7: Integrate Configuration UI into Main App
**File**: `app/app.py`
**Estimated Time**: 1 hour
**Dependencies**: Task 3

**Implementation Steps**:
1. Import and integrate configuration UI component
2. Add provider status indicator
3. Implement configuration validation before proceeding
4. Update sidebar layout

**Acceptance Criteria**:
- [ ] Configuration UI appears in sidebar
- [ ] Users cannot proceed without valid configuration
- [ ] Clear status indicators for connection state
- [ ] Intuitive user flow

#### Task 8: Update All Component Files
**Files**: `app/components/generate_transformations.py`, `app/components/map_study.py`, etc.
**Estimated Time**: 2 hours
**Dependencies**: Task 2, Task 4

**Implementation Steps**:
1. Update all components to use new AI provider interface
2. Ensure consistent error handling
3. Update progress indicators
4. Test all functionality

**Acceptance Criteria**:
- [ ] All existing features work with new provider system
- [ ] Consistent user experience across providers
- [ ] No functionality regression

#### Task 9: Enhanced Error Handling and User Feedback
**Files**: All component files
**Estimated Time**: 1 hour
**Dependencies**: All previous tasks

**Implementation Steps**:
1. Implement comprehensive error handling
2. Add user-friendly error messages
3. Create connection status indicators
4. Add retry mechanisms for transient failures

**Acceptance Criteria**:
- [ ] Clear error messages for all failure scenarios
- [ ] Graceful degradation when possible
- [ ] User guidance for resolving issues

### Phase 3: Docker Containerization (Tasks 10-13)

#### Task 10: Create Dockerfile
**File**: `docker/Dockerfile`
**Estimated Time**: 2 hours
**Dependencies**: None

**Implementation Steps**:
1. Create multi-stage Docker build
2. Use Python 3.9+ base image
3. Install system dependencies
4. Copy application code
5. Set up proper permissions
6. Configure entry point

**Acceptance Criteria**:
- [ ] Multi-stage build for optimization
- [ ] All dependencies installed correctly
- [ ] Proper file permissions
- [ ] Streamlit runs correctly in container

#### Task 11: Create Docker Compose Configuration
**File**: `docker/docker-compose.yml`
**Estimated Time**: 1 hour
**Dependencies**: Task 10

**Implementation Steps**:
1. Create development docker-compose setup
2. Add environment variable configuration
3. Set up volume mounts for development
4. Configure networking

**Acceptance Criteria**:
- [ ] Easy development setup with docker-compose
- [ ] Environment variables properly configured
- [ ] Volume mounts for live development

#### Task 12: Create Environment Configuration
**Files**: `.env.example`, `docker/.dockerignore`
**Estimated Time**: 0.5 hours
**Dependencies**: Task 1

**Implementation Steps**:
1. Create comprehensive .env.example
2. Document all configuration options
3. Create .dockerignore file
4. Update .gitignore if needed

**Acceptance Criteria**:
- [ ] Complete environment variable documentation
- [ ] Secure defaults
- [ ] Proper Docker ignore patterns

#### Task 13: Container Testing and Optimization
**Estimated Time**: 1 hour
**Dependencies**: Task 10, Task 11

**Implementation Steps**:
1. Test container build process
2. Verify all providers work in container
3. Optimize image size
4. Test with different configurations

**Acceptance Criteria**:
- [ ] Container builds successfully
- [ ] All AI providers work in container
- [ ] Reasonable image size
- [ ] Proper resource usage

### Phase 4: Documentation and Testing (Tasks 14-16)

#### Task 14: Update Dependencies
**Files**: `requirements.txt`, `environment.yml`
**Estimated Time**: 0.5 hours
**Dependencies**: All implementation tasks

**Implementation Steps**:
1. Add new dependencies with versions
2. Update conda environment file
3. Test dependency installation
4. Document version requirements

**Acceptance Criteria**:
- [ ] All new dependencies included
- [ ] Version constraints specified
- [ ] Clean installation process

#### Task 15: Comprehensive Documentation Update
**File**: `README.md`
**Estimated Time**: 1.5 hours
**Dependencies**: All previous tasks

**Implementation Steps**:
1. Update installation instructions
2. Document multi-provider setup
3. Add Docker usage instructions
4. Create troubleshooting guide
5. Update examples and screenshots

**Acceptance Criteria**:
- [ ] Clear setup instructions for each provider
- [ ] Docker usage documented
- [ ] Troubleshooting guide included
- [ ] Examples updated

#### Task 16: Integration Testing
**Estimated Time**: 2 hours
**Dependencies**: All previous tasks

**Implementation Steps**:
1. Test all providers with real data
2. Verify Docker deployment
3. Test configuration persistence
4. Validate error handling
5. Performance testing

**Acceptance Criteria**:
- [ ] All providers work correctly
- [ ] Docker deployment successful
- [ ] No functionality regression
- [ ] Performance acceptable

## Success Criteria

### Functional Requirements
- [ ] Support for Ollama, OpenAI, Anthropic, and Azure OpenAI providers
- [ ] User-friendly configuration interface
- [ ] API key management and validation
- [ ] All existing functionality preserved
- [ ] Docker containerization working

### Non-Functional Requirements
- [ ] Performance comparable to original tool
- [ ] Secure handling of API keys
- [ ] Clear error messages and user guidance
- [ ] Comprehensive documentation
- [ ] Easy deployment process

### Technical Requirements
- [ ] Clean, maintainable code following project guidelines
- [ ] Proper error handling and logging
- [ ] Type hints and documentation
- [ ] No hardcoded credentials
- [ ] Backward compatibility where possible

## Risk Assessment

### High Risk
- **Provider API Changes**: Different providers may have different capabilities
- **Mitigation**: Thorough testing and graceful degradation

### Medium Risk
- **Docker Complexity**: Container networking and environment setup
- **Mitigation**: Comprehensive testing and documentation

### Low Risk
- **Configuration Persistence**: Streamlit session state management
- **Mitigation**: Fallback to environment variables

## Timeline Estimate

**Total Estimated Time**: 18 hours

- **Phase 1**: 8.5 hours (Core Infrastructure)
- **Phase 2**: 4 hours (UI Integration)
- **Phase 3**: 4.5 hours (Docker)
- **Phase 4**: 4 hours (Documentation & Testing)

## Next Steps

1. Review and approve this implementation plan
2. Begin with Phase 1, Task 1 (Multi-Provider Configuration)
3. Test each task thoroughly before proceeding
4. Maintain existing functionality throughout development
5. Document any deviations from the plan

## Notes

- All existing functionality must be preserved
- Security is paramount - no hardcoded API keys
- User experience should be intuitive and error-free
- Docker container should be production-ready
- Documentation must be comprehensive and up-to-date
