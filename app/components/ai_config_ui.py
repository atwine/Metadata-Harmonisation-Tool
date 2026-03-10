"""
AI Configuration UI Component

This module provides Streamlit UI components for configuring AI providers,
including provider selection, API key input, model selection, and connection testing.
"""

import os
import streamlit as st
from typing import Optional, Dict, Any
from config import ModelConfig, AIProvider
from .ai_provider import create_ai_provider, AIProviderError
import logging
from .monitor import get_ai_monitor

logger = logging.getLogger(__name__)


# Cached helper: list models from a running Ollama server
# This keeps UI snappy and avoids repeated network calls on every rerun.
@st.cache_data(show_spinner=False)
def _list_ollama_models_cached(host: str):
    """Return a sorted list of model names available on the Ollama server.

    Tries to handle both dict and attribute-style responses from the client.
    Returns an empty list on any error (UI will fall back to text inputs).
    """
    try:
        import ollama
        client = ollama.Client(host=host)
        resp = client.list()
        # Normalize response
        if hasattr(resp, 'models'):
            items = getattr(resp, 'models', [])
        elif isinstance(resp, dict):
            items = resp.get('models', [])
        else:
            items = []
        names = []
        for m in items:
            # Some clients return dicts, others simple objects
            name = None
            if isinstance(m, dict):
                name = m.get('model') or m.get('name')
            else:
                name = getattr(m, 'model', None) or getattr(m, 'name', None)
            if name:
                names.append(name)
        return sorted(set(names))
    except Exception:
        return []

class AIConfigUI:
    """
    Streamlit UI component for AI provider configuration.
    """
    
    def __init__(self):
        """Initialize the AI configuration UI."""
        self.session_key = 'ai_config'
        self.test_key = 'ai_test_result'
        
    def render_provider_selection(self) -> AIProvider:
        """
        Render provider selection dropdown.
        
        Returns:
            Selected AI provider
        """
        provider_options = {
            "Ollama (Local)": AIProvider.OLLAMA,
            "OpenAI": AIProvider.OPENAI,
            "Anthropic": AIProvider.ANTHROPIC,
            "Azure OpenAI": AIProvider.AZURE_OPENAI
        }
        
        # Sticky provider selection: initialize once from existing config/env, then persist via session_state
        if 'ai_provider_select' not in st.session_state:
            try:
                if self.session_key in st.session_state and st.session_state[self.session_key]:
                    existing = st.session_state[self.session_key]
                    reverse_map = {v: k for k, v in provider_options.items()}
                    st.session_state['ai_provider_select'] = reverse_map.get(existing.provider, "Ollama (Local)")
                else:
                    st.session_state['ai_provider_select'] = "Ollama (Local)"
            except Exception:
                st.session_state['ai_provider_select'] = "Ollama (Local)"

        selected_name = st.selectbox(
            "🤖 AI Provider",
            options=list(provider_options.keys()),
            key="ai_provider_select",
            help="Select your preferred AI provider"
        )
        
        return provider_options[selected_name]
    
    def render_ollama_config(self) -> Dict[str, Any]:
        """
        Render Ollama-specific configuration.
        
        Returns:
            Ollama configuration dictionary
        """
        st.markdown("#### 🏠 Ollama Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sticky Base URL: initialize once from env, then persist via session_state across pages/reruns
            # IMPORTANT: Only initialize if key doesn't exist - never overwrite existing user input
            if 'ollama_base_url' not in st.session_state:
                st.session_state['ollama_base_url'] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            base_url = st.text_input(
                "Base URL",
                key="ollama_base_url",
                help="Ollama server URL"
            )
        
        with col2:
            # Consolidated UX: use the unified Connection Test section below
            st.caption("Use the Connection Test below to verify connectivity and models.")
        
        # Model selection: if Ollama server is reachable, show dropdowns of local models
        available_models = _list_ollama_models_cached(base_url)
        if available_models:
            try:
                chat_model = st.selectbox(
                    "Chat Model",
                    options=available_models,
                    index=min(available_models.index("llama3.1:8b") if "llama3.1:8b" in available_models else 0, len(available_models)-1),
                    help="Choose from locally available Ollama models"
                )
            except Exception:
                chat_model = st.selectbox(
                    "Chat Model",
                    options=available_models,
                    help="Choose from locally available Ollama models"
                )
            # Embedding model: prefer nomic-embed-text if present
            default_embed = "nomic-embed-text"
            try:
                embedding_model = st.selectbox(
                    "Embedding Model",
                    options=available_models,
                    index=min(available_models.index(default_embed) if default_embed in available_models else 0, len(available_models)-1),
                    help="Choose an embedding-capable local model"
                )
            except Exception:
                embedding_model = st.selectbox(
                    "Embedding Model",
                    options=available_models,
                    help="Choose an embedding-capable local model"
                )
            st.caption("Models listed from Ollama at the configured Base URL.")
        else:
            # Fallback to text inputs if model listing isn't available
            chat_model = st.text_input(
                "Chat Model",
                value="llama3.1:8b",
                help="Model for chat completions"
            )
            embedding_model = st.text_input(
                "Embedding Model", 
                value="nomic-embed-text",
                help="Model for text embeddings"
            )
        
        return {
            "base_url": base_url,
            "chat_model": chat_model,
            "embedding_model": embedding_model
        }
    
    def render_openai_config(self) -> Dict[str, Any]:
        """
        Render OpenAI-specific configuration.
        
        Returns:
            OpenAI configuration dictionary
        """
        st.markdown("#### 🌐 OpenAI Configuration")
        
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Your OpenAI API key",
            placeholder="sk-..."
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            chat_model = st.selectbox(
                "Chat Model",
                options=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                index=0,
                help="Model for chat completions"
            )
        
        with col2:
            embedding_model = st.selectbox(
                "Embedding Model",
                options=["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"],
                index=1,
                help="Model for text embeddings"
            )
        
        base_url = st.text_input(
            "Base URL (Optional)",
            value="",
            help="Custom API endpoint (leave empty for default)",
            placeholder="https://api.openai.com/v1"
        )
        
        return {
            "api_key": api_key,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "base_url": base_url if base_url else None
        }
    
    def render_anthropic_config(self) -> Dict[str, Any]:
        """
        Render Anthropic-specific configuration.
        
        Returns:
            Anthropic configuration dictionary
        """
        st.markdown("#### 🧠 Anthropic Configuration")
        
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Your Anthropic API key",
            placeholder="sk-ant-..."
        )
        
        chat_model = st.selectbox(
            "Chat Model",
            options=[
                "claude-3-5-sonnet-20241022", 
                "claude-3-haiku-20240307", 
                "claude-3-opus-20240229"
            ],
            index=0,
            help="Model for chat completions"
        )
        
        st.warning(
            "⚠️ Note: Anthropic doesn't provide embedding models. Embeddings will fall back to Ollama if available."
        )
        
        base_url = st.text_input(
            "Base URL (Optional)",
            value="",
            help="Custom API endpoint (leave empty for default)",
            placeholder="https://api.anthropic.com"
        )
        
        return {
            "api_key": api_key,
            "chat_model": chat_model,
            "embedding_model": "nomic-embed-text",  # Fallback to Ollama
            "base_url": base_url if base_url else None
        }
    
    def render_azure_openai_config(self) -> Dict[str, Any]:
        """
        Render Azure OpenAI-specific configuration.
        
        Returns:
            Azure OpenAI configuration dictionary
        """
        st.markdown("#### ☁️ Azure OpenAI Configuration")
        
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Your Azure OpenAI API key"
        )
        
        endpoint = st.text_input(
            "Endpoint",
            help="Your Azure OpenAI endpoint",
            placeholder="https://your-resource.openai.azure.com/"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            chat_model = st.text_input(
                "Chat Deployment",
                help="Name of your chat model deployment",
                placeholder="gpt-4"
            )
        
        with col2:
            embedding_model = st.text_input(
                "Embedding Deployment",
                help="Name of your embedding model deployment",
                placeholder="text-embedding-ada-002"
            )
        
        api_version = st.text_input(
            "API Version",
            value="2024-02-01",
            help="Azure OpenAI API version"
        )
        
        return {
            "api_key": api_key,
            "endpoint": endpoint,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
            "api_version": api_version
        }
    
    def render_connection_test(self, config: ModelConfig) -> None:
        """
        Render connection test section.
        
        Args:
            config: ModelConfig instance to test
        """
        st.markdown("#### 🔍 Connection Test")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("Test Connection", key="test_connection"):
                with st.spinner("Testing connection..."):
                    try:
                        provider = create_ai_provider(config)
                        success, message = provider.validate_connection()
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.session_state[self.test_key] = True
                        else:
                            st.error(f"❌ {message}")
                            st.session_state[self.test_key] = False
                            
                    except Exception as e:
                        st.error(f"❌ Connection test failed: {str(e)}")
                        st.session_state[self.test_key] = False
        
        with col2:
            if self.test_key in st.session_state:
                if st.session_state[self.test_key]:
                    st.success("Connection verified ✅")
                else:
                    st.error("Connection failed ❌")
    
    def render_provider_info(self, config: ModelConfig) -> None:
        """
        Render provider information panel.
        
        Args:
            config: ModelConfig instance
        """
        try:
            provider = create_ai_provider(config)
            info = provider.get_provider_info()
            
            with st.container(border=True):
                st.success("**Current Configuration**")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Provider**")
                    st.markdown(f"> {info['provider'].title()}")
                    st.markdown("**Chat Model**")
                    st.markdown(f"> {info['chat_model']}")
                with col2:
                    st.markdown("**Embedding Model**")
                    st.markdown(f"> {info['embedding_model']}")
                    if info.get("base_url"):
                        st.markdown("**Base URL**")
                        st.markdown(f"> {info['base_url']}")
                    
        except Exception as e:
            st.error(f"Error displaying provider info: {str(e)}")
    
    def render_configuration_panel(self) -> Optional[ModelConfig]:
        """
        Render the complete configuration panel.
        
        Returns:
            ModelConfig instance if configuration is valid, None otherwise
        """
        st.sidebar.markdown("## 🤖 AI Configuration")
        
        # Provider selection
        provider = self.render_provider_selection()
        
        # Provider-specific configuration
        config_data = {}
        
        if provider == AIProvider.OLLAMA:
            config_data = self.render_ollama_config()
        elif provider == AIProvider.OPENAI:
            config_data = self.render_openai_config()
        elif provider == AIProvider.ANTHROPIC:
            config_data = self.render_anthropic_config()
        elif provider == AIProvider.AZURE_OPENAI:
            config_data = self.render_azure_openai_config()
        
        # Create configuration
        try:
            config = ModelConfig()
            config.provider = provider
            
            # Set provider-specific configuration
            if provider == AIProvider.OLLAMA:
                config.base_url = config_data.get('base_url', 'http://localhost:11434')
                config.chat_model = config_data.get('chat_model', 'llama3.1:8b')
                config.embedding_model = config_data.get('embedding_model', 'nomic-embed-text')
            elif provider == AIProvider.OPENAI:
                config.api_key = config_data.get('api_key', '')
                config.chat_model = config_data.get('chat_model', 'gpt-4o')
                config.embedding_model = config_data.get('embedding_model', 'text-embedding-3-small')
                config.base_url = config_data.get('base_url', 'https://api.openai.com/v1')
            elif provider == AIProvider.ANTHROPIC:
                config.api_key = config_data.get('api_key', '')
                config.chat_model = config_data.get('chat_model', 'claude-3-sonnet-20240229')
                config.base_url = config_data.get('base_url', 'https://api.anthropic.com')
            elif provider == AIProvider.AZURE_OPENAI:
                config.api_key = config_data.get('api_key', '')
                config.chat_model = config_data.get('chat_model', 'gpt-4o')
                config.embedding_model = config_data.get('embedding_model', 'text-embedding-3-small')
                config.base_url = config_data.get('base_url', '')
            
            # Store in session state
            st.session_state[self.session_key] = config

            # Global request timeout configuration
            st.markdown("#### ⏱️ Request Timeout")
            timeout_val = st.number_input(
                "Request timeout (seconds)",
                min_value=5,
                max_value=120,
                value=int(getattr(config, 'request_timeout', 30) or 30),
                help="Maximum time to wait for AI provider responses before timing out"
            )
            # Persist timeout on the ModelConfig
            try:
                config.request_timeout = int(timeout_val)
            except Exception:
                config.request_timeout = 30

            # Render connection test
            self.render_connection_test(config)
            
            # Render provider info
            self.render_provider_info(config)
            
            # Render simple AI usage metrics
            try:
                monitor = get_ai_monitor()
                stats = monitor.as_dict()
                st.sidebar.markdown("#### 📊 AI Usage (Session)")
                st.sidebar.write({
                    'calls_total': stats.get('calls_total'),
                    'chat_calls': stats.get('chat_calls'),
                    'embed_calls': stats.get('embed_calls'),
                    'success': stats.get('success'),
                    'errors': stats.get('errors'),
                    'prompt_tokens(~)': stats.get('prompt_tokens'),
                    'completion_tokens(~)': stats.get('completion_tokens'),
                    'success_rate(%)': stats.get('success_rate'),
                })
                if st.sidebar.button('Reset AI Usage Metrics'):
                    monitor.reset()
                    st.sidebar.success('AI usage metrics reset for this session.')
            except Exception:
                pass
            
            return config
            
        except Exception as e:
            st.sidebar.error(f"Configuration error: {str(e)}")
            return None
    
    def is_configured(self) -> bool:
        """
        Check if AI provider is properly configured.
        
        Returns:
            True if configured, False otherwise
        """
        return (self.session_key in st.session_state and 
                st.session_state[self.session_key] is not None)
    
    def get_config(self) -> Optional[ModelConfig]:
        """
        Get the current AI configuration from session state.
        
        Returns:
            ModelConfig instance or None if not configured
        """
        return st.session_state.get(self.session_key)
    
    def render_status_indicator(self) -> None:
        """
        Render AI provider status indicator in the main area.
        """
        if self.is_configured():
            config = self.get_config()
            if config:
                provider_name = config.provider.value.title()
                st.success(f"🤖 AI Provider: {provider_name} - Ready")
            else:
                st.error("🤖 AI Provider: Configuration Error")
        else:
            st.warning("🤖 AI Provider: Not Configured - Please configure in sidebar")

# Global instance for easy access
ai_config_ui = AIConfigUI()
