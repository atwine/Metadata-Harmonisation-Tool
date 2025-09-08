"""
AI Provider Abstraction Layer

This module provides a unified interface for interacting with different AI providers
while handling provider-specific differences, error handling, and retry logic.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Union
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import ModelConfig, AIProvider
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from .monitor import get_ai_monitor

logger = logging.getLogger(__name__)

class AIProviderError(Exception):
    """Custom exception for AI provider errors"""
    pass

class AIProviderWrapper:
    """
    Wrapper class that provides a unified interface for AI operations
    across different providers while handling retries and error management.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the AI provider wrapper.
        
        Args:
            config: ModelConfig instance with provider settings
        """
        self.config = config
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        # Default timeout per request (seconds)
        self.request_timeout = getattr(self.config, 'request_timeout', 30) or 30
        
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            AIProviderError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    
        raise AIProviderError(f"Operation failed after {self.max_retries} attempts: {str(last_exception)}")

    def _with_timeout(self, func, timeout_seconds: int, *args, **kwargs):
        """Run a callable with a timeout using a thread executor."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeout:
                future.cancel()
                raise AIProviderError(f"Request timed out after {timeout_seconds} seconds")
    
    def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a chat response using the configured provider.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated response text
            
        Raises:
            AIProviderError: If response generation fails
        """
        def _generate():
            try:
                client = self.config.get_client()
                if not client:
                    raise AIProviderError("Failed to get AI client")
                
                if self.config.provider == AIProvider.OLLAMA:
                    response = client.chat(
                        model=self.config.chat_model,
                        messages=messages,
                        **kwargs
                    )
                    content = response['message']['content']
                elif self.config.provider == AIProvider.OPENAI:
                    response = client.chat.completions.create(
                        model=self.config.chat_model,
                        messages=messages,
                        **kwargs
                    )
                    content = response.choices[0].message.content
                elif self.config.provider == AIProvider.ANTHROPIC:
                    # Convert messages to Anthropic format
                    system_msg = None
                    user_messages = []
                    for msg in messages:
                        if msg['role'] == 'system':
                            system_msg = msg['content']
                        else:
                            user_messages.append(msg)
                    
                    response = client.messages.create(
                        model=self.config.chat_model,
                        max_tokens=kwargs.get('max_tokens', 1000),
                        system=system_msg,
                        messages=user_messages
                    )
                    content = response.content[0].text
                elif self.config.provider == AIProvider.AZURE_OPENAI:
                    response = client.chat.completions.create(
                        model=self.config.chat_model,
                        messages=messages,
                        **kwargs
                    )
                    content = response.choices[0].message.content
                else:
                    raise AIProviderError(f"Unsupported provider: {self.config.provider}")
                
                if not content:
                    raise AIProviderError("Empty response received from provider")
                return content
            except Exception as e:
                raise AIProviderError(f"Chat response generation failed: {str(e)}")
        
        # Monitoring: estimate prompt chars
        try:
            prompt_chars = sum(len(m.get('content', '')) for m in messages if isinstance(m, dict))
        except Exception:
            prompt_chars = 0
        monitor = get_ai_monitor()

        try:
            content = self._retry_with_backoff(lambda: self._with_timeout(_generate, self.request_timeout))
            monitor.record_chat(prompt_chars=prompt_chars, completion_chars=len(content or ''), success=True)
            return content
        except AIProviderError:
            monitor.record_chat(prompt_chars=prompt_chars, completion_chars=0, success=False)
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
            
        Raises:
            AIProviderError: If embedding generation fails
        """
        def _generate():
            try:
                client = self.config.get_client()
                if not client:
                    raise AIProviderError("Failed to get AI client")
                
                if self.config.provider == AIProvider.OLLAMA:
                    response = client.embeddings(
                        model=self.config.embedding_model,
                        prompt=text
                    )
                    embedding = response['embedding']
                elif self.config.provider == AIProvider.OPENAI:
                    response = client.embeddings.create(
                        model=self.config.embedding_model,
                        input=text
                    )
                    embedding = response.data[0].embedding
                elif self.config.provider == AIProvider.ANTHROPIC:
                    # Anthropic doesn't have embeddings API, use OpenAI-compatible fallback
                    raise AIProviderError("Anthropic doesn't support embeddings")
                elif self.config.provider == AIProvider.AZURE_OPENAI:
                    response = client.embeddings.create(
                        model=self.config.embedding_model,
                        input=text
                    )
                    embedding = response.data[0].embedding
                else:
                    raise AIProviderError(f"Unsupported provider: {self.config.provider}")
                
                if not embedding:
                    raise AIProviderError("Empty embedding received from provider")
                return embedding
            except Exception as e:
                raise AIProviderError(f"Embedding generation failed: {str(e)}")
        monitor = get_ai_monitor()
        try:
            result = self._retry_with_backoff(lambda: self._with_timeout(_generate, self.request_timeout))
            monitor.record_embed(success=True)
            return result
        except AIProviderError:
            monitor.record_embed(success=False)
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding lists
            
        Raises:
            AIProviderError: If batch embedding generation fails
        """
        embeddings = []
        
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = []
                
                for text in batch:
                    embedding = self.generate_embedding(text)
                    batch_embeddings.append(embedding)
                
                embeddings.extend(batch_embeddings)
                
                # Add small delay between batches to avoid rate limiting
                if i + batch_size < len(texts):
                    time.sleep(0.1)
                    
            return embeddings
            
        except Exception as e:
            raise AIProviderError(f"Batch embedding generation failed: {str(e)}")
    
    def validate_connection(self) -> tuple[bool, str]:
        """
        Validate connection to the AI provider.
        
        Returns:
            tuple[bool, str]: (success, message)
        """
        try:
            return self.config.validate_models()
        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False, f"Connection validation failed: {str(e)}"
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current provider configuration.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.config.provider.value,
            "chat_model": self.config.chat_model,
            "embedding_model": self.config.embedding_model,
            "base_url": getattr(self.config, 'base_url', None),
            "has_api_key": bool(self.config.api_key) if hasattr(self.config, 'api_key') else False
        }
    
    def normalize_response_format(self, response: Any) -> Dict[str, Any]:
        """
        Normalize response format across different providers.
        
        Args:
            response: Raw response from provider
            
        Returns:
            Normalized response dictionary
        """
        if self.config.provider == AIProvider.OLLAMA:
            if hasattr(response, 'message'):
                return {
                    "content": response.message.content,
                    "role": response.message.role,
                    "model": response.model,
                    "provider": "ollama"
                }
        
        elif self.config.provider in [AIProvider.OPENAI, AIProvider.AZURE_OPENAI]:
            if hasattr(response, 'choices') and response.choices:
                return {
                    "content": response.choices[0].message.content,
                    "role": response.choices[0].message.role,
                    "model": response.model,
                    "provider": self.config.provider.value
                }
        
        elif self.config.provider == AIProvider.ANTHROPIC:
            if hasattr(response, 'content') and response.content:
                return {
                    "content": response.content[0].text,
                    "role": "assistant",
                    "model": response.model,
                    "provider": "anthropic"
                }
        
        # Fallback for unknown format
        return {
            "content": str(response),
            "role": "assistant",
            "model": "unknown",
            "provider": self.config.provider.value
        }
    
    def handle_provider_error(self, error: Exception) -> str:
        """
        Handle provider-specific errors and return user-friendly messages.
        
        Args:
            error: Exception from provider
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "quota" in error_str:
            return "Rate limit exceeded. Please wait a moment and try again."
        
        elif "authentication" in error_str or "api key" in error_str:
            return "Authentication failed. Please check your API key."
        
        elif "connection" in error_str or "network" in error_str:
            return "Connection failed. Please check your internet connection and try again."
        
        elif "model" in error_str and "not found" in error_str:
            return "The specified model is not available. Please check your model configuration."
        
        elif self.config.provider == AIProvider.OLLAMA and "connection refused" in error_str:
            return "Cannot connect to Ollama. Please ensure Ollama is running on your system."
        
        else:
            return f"An error occurred: {str(error)}"

def create_ai_provider(config: ModelConfig) -> AIProviderWrapper:
    """
    Factory function to create an AI provider wrapper.
    
    Args:
        config: ModelConfig instance
        
    Returns:
        AIProviderWrapper instance
    """
    return AIProviderWrapper(config)

def get_ai_provider_from_session() -> Optional[AIProviderWrapper]:
    """
    Get AI provider from Streamlit session state.
    
    Returns:
        AIProviderWrapper instance or None if not configured
    """
    if 'ai_config' in st.session_state:
        return create_ai_provider(st.session_state.ai_config)
    return None
