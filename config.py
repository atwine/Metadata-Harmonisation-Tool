"""
Configuration module for the Metadata Harmonisation Tool.
Supports multiple AI providers: Ollama, OpenAI, and other compatible APIs.
"""

import os
import streamlit as st
from enum import Enum
from typing import Optional, Dict, Any, List
import ollama
import openai
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"

class ModelConfig:
    """Configuration class for AI model settings"""
    
    def __init__(self):
        self.provider = None
        self.chat_model = None
        self.embedding_model = None
        self.api_key = None
        self.base_url = None
        self.client = None
        
    def setup_from_env(self):
        """Load configuration from environment variables"""
        provider = os.getenv('AI_PROVIDER', 'ollama').lower()
        
        if provider == 'ollama':
            self.provider = AIProvider.OLLAMA
            self.chat_model = os.getenv('OLLAMA_CHAT_MODEL', 'llama3.1:8b')
            self.embedding_model = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
            self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            
        elif provider == 'openai':
            self.provider = AIProvider.OPENAI
            self.chat_model = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4')
            self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            self.api_key = os.getenv('OPENAI_API_KEY')
            self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            
        elif provider == 'anthropic':
            self.provider = AIProvider.ANTHROPIC
            self.chat_model = os.getenv('ANTHROPIC_CHAT_MODEL', 'claude-3-sonnet-20240229')
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            self.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
            
        elif provider == 'azure_openai':
            self.provider = AIProvider.AZURE_OPENAI
            self.chat_model = os.getenv('AZURE_OPENAI_CHAT_MODEL', 'gpt-4')
            self.embedding_model = os.getenv('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            self.api_key = os.getenv('AZURE_OPENAI_API_KEY')
            self.base_url = os.getenv('AZURE_OPENAI_ENDPOINT')
            
    def setup_from_streamlit(self):
        """Load configuration from Streamlit session state/UI"""
        if 'ai_config' not in st.session_state:
            st.session_state.ai_config = {}
            
        config = st.session_state.ai_config
        
        self.provider = AIProvider(config.get('provider', 'ollama'))
        self.chat_model = config.get('chat_model', '')
        self.embedding_model = config.get('embedding_model', '')
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', '')
        
    def get_client(self):
        """Initialize and return the appropriate AI client"""
        if self.client:
            return self.client
            
        try:
            if self.provider == AIProvider.OLLAMA:
                self.client = ollama.Client(host=self.base_url)
                # Test connection
                self.client.list()
                
            elif self.provider == AIProvider.OPENAI:
                if not self.api_key:
                    raise ValueError("OpenAI API key is required")
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                
            elif self.provider == AIProvider.ANTHROPIC:
                if not self.api_key:
                    raise ValueError("Anthropic API key is required")
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                
            elif self.provider == AIProvider.AZURE_OPENAI:
                if not self.api_key or not self.base_url:
                    raise ValueError("Azure OpenAI API key and endpoint are required")
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.base_url,
                    api_version="2024-02-01"
                )
                
            return self.client
            
        except Exception as e:
            st.error(f"Failed to initialize {self.provider.value} client: {str(e)}")
            return None
            
    def validate_models(self) -> tuple[bool, str]:
        """Validate that required models are available
        
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        try:
            client = self.get_client()
            if not client:
                return False, "Failed to initialize AI client"
                
            if self.provider == AIProvider.OLLAMA:
                try:
                    response = client.list()
                    available_models = [m.model for m in response.models]
                    
                    chat_found = any(model.startswith(self.chat_model) for model in available_models)
                    embed_found = any(model.startswith(self.embedding_model) for model in available_models)
                    
                    if not chat_found:
                        return False, f"Chat model '{self.chat_model}' not found in Ollama. Available models: {available_models}"
                    if not embed_found:
                        return False, f"Embedding model '{self.embedding_model}' not found in Ollama. Available models: {available_models}"
                        
                    return True, "Models validated successfully"
                except Exception as e:
                    return False, f"Failed to connect to Ollama: {str(e)}"
                
            elif self.provider in [AIProvider.OPENAI, AIProvider.AZURE_OPENAI]:
                # Test with a simple API call
                try:
                    test_response = client.chat.completions.create(
                        model=self.chat_model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    return True, "OpenAI models validated successfully"
                except Exception as e:
                    return False, f"OpenAI model validation failed: {str(e)}"
                
            elif self.provider == AIProvider.ANTHROPIC:
                # Test with a simple API call
                try:
                    import anthropic
                    test_response = client.messages.create(
                        model=self.chat_model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    return True, "Anthropic models validated successfully"
                except Exception as e:
                    return False, f"Anthropic model validation failed: {str(e)}"
                
        except Exception as e:
            logger.error(f"Model validation error: {str(e)}")
            return False, f"Model validation failed: {str(e)}"
            
        return False, "Unknown provider"
        
    def generate_chat_response(self, messages: list, **kwargs) -> str:
        """Generate chat response using the configured provider"""
        client = self.get_client()
        if not client:
            raise RuntimeError("AI client not initialized")
            
        try:
            if self.provider == AIProvider.OLLAMA:
                response = client.chat(
                    model=self.chat_model,
                    messages=messages,
                    **kwargs
                )
                return response['message']['content']
                
            elif self.provider in [AIProvider.OPENAI, AIProvider.AZURE_OPENAI]:
                response = client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
                
            elif self.provider == AIProvider.ANTHROPIC:
                # Convert messages format for Anthropic
                system_message = ""
                user_messages = []
                
                for msg in messages:
                    if msg['role'] == 'system':
                        system_message = msg['content']
                    else:
                        user_messages.append(msg)
                
                response = client.messages.create(
                    model=self.chat_model,
                    system=system_message,
                    messages=user_messages,
                    max_tokens=kwargs.get('max_tokens', 1000),
                    **{k: v for k, v in kwargs.items() if k != 'max_tokens'}
                )
                return response.content[0].text
                
        except Exception as e:
            st.error(f"Chat generation failed: {str(e)}")
            raise
            
    def generate_embeddings(self, texts: list) -> list:
        """Generate embeddings using the configured provider"""
        client = self.get_client()
        if not client:
            raise RuntimeError("AI client not initialized")
            
        try:
            if self.provider == AIProvider.OLLAMA:
                embeddings = []
                for text in texts:
                    response = client.embeddings(
                        model=self.embedding_model,
                        prompt=text
                    )
                    embeddings.append(response['embedding'])
                return embeddings
                
            elif self.provider in [AIProvider.OPENAI, AIProvider.AZURE_OPENAI]:
                response = client.embeddings.create(
                    model=self.embedding_model,
                    input=texts
                )
                return [embedding.embedding for embedding in response.data]
                
            elif self.provider == AIProvider.ANTHROPIC:
                # Anthropic doesn't have embeddings API, would need alternative
                raise NotImplementedError("Anthropic doesn't support embeddings. Use OpenAI or Ollama for embedding functionality.")
                
        except Exception as e:
            st.error(f"Embedding generation failed: {str(e)}")
            raise

# Global config instance
model_config = ModelConfig()
