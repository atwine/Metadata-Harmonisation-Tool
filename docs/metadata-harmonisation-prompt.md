# Project Prompt Template
<!-- 
  This is your project brief template. Copy this file and fill it out to define WHAT you want to build.
  The AI will use this to create a comprehensive step-by-step implementation plan.
-->

## 1. High-Level Goal
<!-- 
  **Your Goal:** In one or two sentences, describe the main objective of the project.
  **Example:** "I want to build a web app that converts currency using a public API."
-->

I want to enhance the existing Metadata Harmonisation Tool to support multiple AI providers (Ollama, OpenAI, Anthropic, Azure OpenAI) with flexible model selection and containerize it with Docker for easy deployment and distribution.

## 2. Core Features & Requirements
<!-- 
  **Your Goal:** List the essential features as a bulleted list. Be specific and detailed.
  **Example:**
  - Must have a dropdown to select the 'from' and 'to' currencies
  - Must have an input box for the amount
  - Must display the converted amount clearly
  - Must show the last updated time for the exchange rate
-->

- Must have a configuration UI in Streamlit sidebar to select AI provider (Ollama, OpenAI, Anthropic, Azure OpenAI)
- Must allow users to input their own API keys for cloud providers (OpenAI, Anthropic, Azure)
- Must support local Ollama connection with automatic model detection
- Must validate model availability before allowing user to proceed
- Must maintain all existing functionality (variable mapping, descriptions, transformations)
- Must be fully containerized with Docker for easy deployment
- Must include environment variable configuration for different deployment scenarios
- Must have clear error handling and user feedback for connection issues
- Must preserve the current Streamlit interface and workflow
- Must support both chat models (for descriptions/recommendations) and embedding models (for similarity matching)

## 3. Technology Stack
<!-- 
  **Your Goal:** List the programming languages, libraries, and frameworks you want to use.
  **Example:**
  - Language: JavaScript
  - Framework: React
  - Libraries: axios, Material-UI
  - Database: PostgreSQL
-->

- Language: Python 3.9+
- Framework: Streamlit (existing)
- Libraries: ollama, openai, anthropic, python-dotenv, fsspec, pandas, scipy
- Containerization: Docker with multi-stage builds
- Configuration: Environment variables and Streamlit session state
- File System: fsspec for flexible file handling

## 4. Code Examples
<!-- 
  **Your Goal:** (Optional but powerful) If you have specific code patterns or styles, 
  create files in the `examples/` folder and reference them here.
  **Example:** "See `examples/my-api-handler.js` for how I want API calls to be structured."
-->

The existing codebase in `app/components/util.py` shows the current Ollama integration pattern. The new configuration system should follow similar patterns but be provider-agnostic. See existing `app/components/generate_descriptions.py` and `app/components/get_recommendations.py` for how AI calls are currently structured.

## 5. Documentation & References
<!-- 
  **Your Goal:** Provide links to official documentation for any libraries or APIs needed.
  This helps ensure current and correct implementation methods.
  **Example:** 
  - [React Docs](https://react.dev/)
  - [Currency API Docs](https://exchangerate-api.com/docs)
-->

- [Ollama Python Library](https://github.com/ollama/ollama-python)
- [OpenAI Python Library](https://github.com/openai/openai-python)
- [Anthropic Python Library](https://github.com/anthropics/anthropic-sdk-python)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Python-dotenv Documentation](https://pypi.org/project/python-dotenv/)

## 6. Other Considerations & Gotchas
<!-- 
  **Your Goal:** List anything else important. Tricky parts? Specific constraints? Performance requirements?
  **Example:** "The API has a rate limit of 10 requests per minute, so add error handling for that."
-->

- Different AI providers have different message formats (especially Anthropic vs OpenAI)
- Embedding models are not available for all providers (Anthropic doesn't have embeddings API)
- API rate limits vary by provider and need appropriate error handling
- Docker container needs to handle both local Ollama connections and external API calls
- Environment variables must be properly secured (no hardcoded API keys)
- The current tool requires Unix-like filesystem, so Docker should use Linux base image
- Model names in Ollama can have version suffixes that need flexible matching
- Connection timeouts and retry logic needed for reliable operation

## 7. Success Criteria
<!-- 
  **Your Goal:** Define what "done" looks like. How will you know the project is successful?
  **Example:** 
  - User can convert between any two supported currencies
  - Conversion happens in under 2 seconds
  - Error messages are clear and helpful
-->

- User can successfully switch between different AI providers through the UI
- All existing functionality works with any configured AI provider
- Docker container runs successfully with simple `docker run` command
- Clear error messages guide users when API keys are missing or invalid
- Models are automatically validated before use
- Configuration persists across sessions appropriately
- Container can be deployed on any Docker-compatible platform
- Documentation includes clear setup instructions for each AI provider
- No breaking changes to existing workflow or file formats
