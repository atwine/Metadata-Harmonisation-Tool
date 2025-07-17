#!/usr/bin/env python3
"""
Configuration Validation Script for Metadata Harmonisation Tool

This script validates environment configuration and AI provider connectivity
to ensure the application is properly configured before deployment.

Usage:
    python validate_config.py
    python validate_config.py --provider ollama
    python validate_config.py --all-providers
"""

import os
import sys
import argparse
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from components.ai_provider import AIProviderWrapper
    from config import ModelConfig, AIProvider
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


class ValidationStatus(Enum):
    PASS = "✅"
    FAIL = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"


@dataclass
class ValidationResult:
    status: ValidationStatus
    message: str
    details: Optional[str] = None


class ConfigValidator:
    """Validates environment configuration and AI provider connectivity."""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.load_environment()
    
    def load_environment(self):
        """Load environment variables from .env file if it exists."""
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                self.add_result(ValidationStatus.PASS, "Environment file loaded", ".env file found and loaded")
            except Exception as e:
                self.add_result(ValidationStatus.WARNING, "Failed to load .env file", str(e))
        else:
            self.add_result(ValidationStatus.INFO, "No .env file found", "Using system environment variables only")
    
    def add_result(self, status: ValidationStatus, message: str, details: Optional[str] = None):
        """Add a validation result."""
        self.results.append(ValidationResult(status, message, details))
    
    def validate_basic_config(self) -> bool:
        """Validate basic application configuration."""
        print("\n🔍 Validating Basic Configuration...")
        
        # Check required directories
        required_dirs = ['app', 'input', 'output', 'logs']
        for dir_name in required_dirs:
            if os.path.exists(dir_name):
                self.add_result(ValidationStatus.PASS, f"Directory exists: {dir_name}")
            else:
                self.add_result(ValidationStatus.WARNING, f"Directory missing: {dir_name}", 
                              f"Will be created automatically if needed")
        
        # Check required files
        required_files = ['app/app.py', 'config.py', 'requirements.txt']
        for file_name in required_files:
            if os.path.exists(file_name):
                self.add_result(ValidationStatus.PASS, f"File exists: {file_name}")
            else:
                self.add_result(ValidationStatus.FAIL, f"Required file missing: {file_name}")
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.add_result(ValidationStatus.PASS, f"Python version: {python_version.major}.{python_version.minor}")
        else:
            self.add_result(ValidationStatus.FAIL, f"Python version too old: {python_version.major}.{python_version.minor}", 
                          "Python 3.8+ required")
        
        return all(r.status != ValidationStatus.FAIL for r in self.results[-len(required_files)-1:])
    
    def validate_ollama_config(self) -> bool:
        """Validate Ollama configuration and connectivity."""
        print("\n🦙 Validating Ollama Configuration...")
        
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.add_result(ValidationStatus.INFO, f"Ollama base URL: {base_url}")
        
        try:
            # Test connectivity
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                self.add_result(ValidationStatus.PASS, "Ollama server is accessible")
                
                # Check available models
                models = response.json().get('models', [])
                if models:
                    model_names = [model['name'] for model in models]
                    self.add_result(ValidationStatus.PASS, f"Available models: {len(models)}", 
                                  f"Models: {', '.join(model_names[:5])}")
                    
                    # Check for recommended models
                    recommended_models = ['llama3.1:8b', 'nomic-embed-text']
                    for model in recommended_models:
                        if any(model in m for m in model_names):
                            self.add_result(ValidationStatus.PASS, f"Recommended model available: {model}")
                        else:
                            self.add_result(ValidationStatus.WARNING, f"Recommended model not found: {model}",
                                          f"Run: ollama pull {model}")
                else:
                    self.add_result(ValidationStatus.WARNING, "No models available", 
                                  "Pull models with: ollama pull llama3.1:8b")
                return True
            else:
                self.add_result(ValidationStatus.FAIL, f"Ollama server error: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.add_result(ValidationStatus.FAIL, "Cannot connect to Ollama server", 
                          f"Make sure Ollama is running on {base_url}")
            return False
        except Exception as e:
            self.add_result(ValidationStatus.FAIL, f"Ollama validation error: {str(e)}")
            return False
    
    def validate_openai_config(self) -> bool:
        """Validate OpenAI configuration."""
        print("\n🤖 Validating OpenAI Configuration...")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.add_result(ValidationStatus.WARNING, "OpenAI API key not configured", 
                          "Set OPENAI_API_KEY environment variable")
            return False
        
        self.add_result(ValidationStatus.PASS, "OpenAI API key configured")
        
        try:
            # Test API key validity (simple request)
            headers = {'Authorization': f'Bearer {api_key}'}
            response = requests.get('https://api.openai.com/v1/models', headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.add_result(ValidationStatus.PASS, "OpenAI API key is valid")
                return True
            elif response.status_code == 401:
                self.add_result(ValidationStatus.FAIL, "OpenAI API key is invalid")
                return False
            else:
                self.add_result(ValidationStatus.WARNING, f"OpenAI API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.add_result(ValidationStatus.WARNING, f"OpenAI validation error: {str(e)}")
            return False
    
    def validate_anthropic_config(self) -> bool:
        """Validate Anthropic configuration."""
        print("\n🧠 Validating Anthropic Configuration...")
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            self.add_result(ValidationStatus.WARNING, "Anthropic API key not configured", 
                          "Set ANTHROPIC_API_KEY environment variable")
            return False
        
        self.add_result(ValidationStatus.PASS, "Anthropic API key configured")
        
        # Note: Anthropic doesn't have a simple models endpoint, so we'll just validate the key format
        if api_key.startswith('sk-ant-'):
            self.add_result(ValidationStatus.PASS, "Anthropic API key format is valid")
            return True
        else:
            self.add_result(ValidationStatus.WARNING, "Anthropic API key format may be invalid", 
                          "Expected format: sk-ant-...")
            return False
    
    def validate_azure_openai_config(self) -> bool:
        """Validate Azure OpenAI configuration."""
        print("\n☁️ Validating Azure OpenAI Configuration...")
        
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        
        if not api_key:
            self.add_result(ValidationStatus.WARNING, "Azure OpenAI API key not configured")
            return False
        
        if not endpoint:
            self.add_result(ValidationStatus.WARNING, "Azure OpenAI endpoint not configured")
            return False
        
        self.add_result(ValidationStatus.PASS, "Azure OpenAI credentials configured")
        self.add_result(ValidationStatus.INFO, f"Azure endpoint: {endpoint}")
        
        return True
    
    def validate_ai_provider(self, provider: str) -> bool:
        """Validate a specific AI provider by creating and testing it."""
        print(f"\n🧪 Testing AI Provider: {provider}")
        
        try:
            # Create model config
            config = ModelConfig()
            
            if provider == 'ollama':
                config.provider = AIProvider.OLLAMA
                config.chat_model = os.getenv('OLLAMA_CHAT_MODEL', 'llama3.1:8b')
                config.embedding_model = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
                config.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            elif provider == 'openai':
                config.provider = AIProvider.OPENAI
                config.api_key = os.getenv('OPENAI_API_KEY')
                config.chat_model = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
                config.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
                if not config.api_key:
                    self.add_result(ValidationStatus.FAIL, f"No API key for {provider}")
                    return False
            elif provider == 'anthropic':
                config.provider = AIProvider.ANTHROPIC
                config.api_key = os.getenv('ANTHROPIC_API_KEY')
                config.chat_model = os.getenv('ANTHROPIC_CHAT_MODEL', 'claude-3-5-sonnet-20241022')
                if not config.api_key:
                    self.add_result(ValidationStatus.FAIL, f"No API key for {provider}")
                    return False
            elif provider == 'azure_openai':
                config.provider = AIProvider.AZURE_OPENAI
                config.api_key = os.getenv('AZURE_OPENAI_API_KEY')
                config.base_url = os.getenv('AZURE_OPENAI_ENDPOINT')
                config.chat_model = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4o-mini')
                config.embedding_model = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
                if not config.api_key or not config.base_url:
                    self.add_result(ValidationStatus.FAIL, f"Incomplete configuration for {provider}")
                    return False
            
            # Create AI provider wrapper
            ai_provider = AIProviderWrapper(config)
            
            # Test embedding generation (if supported)
            if provider != 'anthropic':  # Anthropic doesn't support embeddings
                try:
                    embedding = ai_provider.generate_embedding("test embedding")
                    if embedding and len(embedding) > 0:
                        self.add_result(ValidationStatus.PASS, f"{provider} embedding generation works", 
                                      f"Generated {len(embedding)}-dimensional embedding")
                    else:
                        self.add_result(ValidationStatus.FAIL, f"{provider} embedding generation failed")
                        return False
                except Exception as e:
                    self.add_result(ValidationStatus.FAIL, f"{provider} embedding error: {str(e)}")
                    return False
            
            # Test chat completion
            try:
                response = ai_provider.generate_chat_response("Hello, this is a test message.")
                if response and len(response.strip()) > 0:
                    self.add_result(ValidationStatus.PASS, f"{provider} chat completion works", 
                                  f"Response: {response[:50]}...")
                else:
                    self.add_result(ValidationStatus.FAIL, f"{provider} chat completion failed")
                    return False
            except Exception as e:
                self.add_result(ValidationStatus.FAIL, f"{provider} chat error: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            self.add_result(ValidationStatus.FAIL, f"{provider} provider creation failed: {str(e)}")
            return False
    
    def validate_docker_config(self) -> bool:
        """Validate Docker configuration."""
        print("\n🐳 Validating Docker Configuration...")
        
        # Check if Docker files exist
        docker_files = ['docker/Dockerfile', 'docker/docker-compose.yml', 'docker/.dockerignore']
        for file_name in docker_files:
            if os.path.exists(file_name):
                self.add_result(ValidationStatus.PASS, f"Docker file exists: {file_name}")
            else:
                self.add_result(ValidationStatus.WARNING, f"Docker file missing: {file_name}")
        
        # Check if Docker is available
        try:
            import subprocess
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.add_result(ValidationStatus.PASS, "Docker is available", result.stdout.strip())
            else:
                self.add_result(ValidationStatus.WARNING, "Docker command failed")
        except Exception as e:
            self.add_result(ValidationStatus.WARNING, "Docker not available", str(e))
        
        return True
    
    def print_results(self):
        """Print all validation results."""
        print("\n" + "="*60)
        print("📋 VALIDATION RESULTS")
        print("="*60)
        
        # Group results by status
        passed = [r for r in self.results if r.status == ValidationStatus.PASS]
        failed = [r for r in self.results if r.status == ValidationStatus.FAIL]
        warnings = [r for r in self.results if r.status == ValidationStatus.WARNING]
        info = [r for r in self.results if r.status == ValidationStatus.INFO]
        
        for result in self.results:
            print(f"{result.status.value} {result.message}")
            if result.details:
                print(f"   {result.details}")
        
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"✅ Passed: {len(passed)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"⚠️  Warnings: {len(warnings)}")
        print(f"ℹ️  Info: {len(info)}")
        
        if failed:
            print(f"\n❌ {len(failed)} critical issues found. Please fix these before proceeding.")
            return False
        elif warnings:
            print(f"\n⚠️  {len(warnings)} warnings found. Review these for optimal configuration.")
            return True
        else:
            print(f"\n✅ All validations passed! Your configuration looks good.")
            return True
    
    def run_validation(self, providers: Optional[List[str]] = None):
        """Run complete validation."""
        print("🚀 Starting Configuration Validation...")
        
        # Basic configuration
        self.validate_basic_config()
        
        # Docker configuration
        self.validate_docker_config()
        
        # AI provider configurations
        if not providers:
            providers = ['ollama']  # Default to Ollama only
        
        for provider in providers:
            if provider == 'ollama':
                if self.validate_ollama_config():
                    self.validate_ai_provider('ollama')
            elif provider == 'openai':
                if self.validate_openai_config():
                    self.validate_ai_provider('openai')
            elif provider == 'anthropic':
                if self.validate_anthropic_config():
                    self.validate_ai_provider('anthropic')
            elif provider == 'azure_openai':
                if self.validate_azure_openai_config():
                    self.validate_ai_provider('azure_openai')
            else:
                self.add_result(ValidationStatus.WARNING, f"Unknown provider: {provider}")
        
        # Print results and return success status
        return self.print_results()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Validate Metadata Harmonisation Tool configuration')
    parser.add_argument('--provider', choices=['ollama', 'openai', 'anthropic', 'azure_openai'],
                       help='Validate specific AI provider')
    parser.add_argument('--all-providers', action='store_true',
                       help='Validate all configured AI providers')
    
    args = parser.parse_args()
    
    # Determine which providers to validate
    providers = []
    if args.all_providers:
        providers = ['ollama', 'openai', 'anthropic', 'azure_openai']
    elif args.provider:
        providers = [args.provider]
    else:
        providers = ['ollama']  # Default
    
    # Run validation
    validator = ConfigValidator()
    success = validator.run_validation(providers)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
