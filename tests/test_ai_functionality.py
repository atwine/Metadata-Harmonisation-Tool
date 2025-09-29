#!/usr/bin/env python3
"""
Test script for AI provider functionality
"""
import sys
sys.path.append('.')
from config import ModelConfig, AIProvider
from app.components.ai_provider import create_ai_provider

def test_ai_functionality():
    """Test core AI provider functionality"""
    print('Testing AI Provider Functionality...')
    
    # Test with Ollama configuration
    config = ModelConfig()
    config.provider = AIProvider.OLLAMA
    config.chat_model = 'llama3.1:8b'
    config.embedding_model = 'nomic-embed-text'
    config.base_url = 'http://localhost:11434'

    try:
        provider = create_ai_provider(config)
        print('✓ AI Provider created successfully')
        
        # Test embedding generation
        print('\nTesting embedding generation...')
        test_text = 'patient age in years'
        embedding = provider.generate_embedding(test_text)
        print(f'✓ Embedding generated: {len(embedding)} dimensions')
        
        # Test chat completion
        print('\nTesting chat completion...')
        messages = [
            {'role': 'user', 'content': 'What does the variable name "age" likely represent in a health study?'}
        ]
        response = provider.generate_chat_response(messages)
        print(f'✓ Chat response generated: {response[:100]}...')
        
        print('\nAll core AI functionality tests passed!')
        return True
        
    except Exception as e:
        print(f'✗ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_ai_functionality()
    sys.exit(0 if success else 1)
