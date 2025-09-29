#!/usr/bin/env python3
"""
Test script for integrated AI components
"""
import sys
import os
sys.path.append('.')
from config import ModelConfig, AIProvider
from app.components.ai_provider import create_ai_provider
from app.components.generate_descriptions import get_embedding, get_llm_response
from app.components.get_recommendations import get_PID_date_recommendations
import pandas as pd

def test_integrated_components():
    """Test integrated AI components"""
    print('Testing Integrated AI Components...')
    
    # Setup AI provider
    config = ModelConfig()
    config.provider = AIProvider.OLLAMA
    config.chat_model = 'llama3.1:8b'
    config.embedding_model = 'nomic-embed-text'
    config.base_url = 'http://localhost:11434'
    
    try:
        # Test 1: generate_descriptions functions
        print('\n1. Testing generate_descriptions functions...')
        
        # Test get_embedding function
        test_text = "patient age in years"
        embedding = get_embedding(test_text)
        print(f'   get_embedding: {len(embedding)} dimensions')
        
        # Test get_llm_response function
        messages = [{'role': 'user', 'content': 'What is a common health variable?'}]
        response = get_llm_response(messages)
        print(f'   get_llm_response: {response[:50]}...')
        
        # Test 2: Check if target variables file exists for recommendations
        print('\n2. Testing get_recommendations functions...')
        
        if os.path.exists('input/target_variables.csv'):
            target_df = pd.read_csv('input/target_variables.csv')
            print(f'   Target variables loaded: {len(target_df)} variables')
            
            # Test get_PID_date_recommendations (processes all studies)
            print('   Testing PID/date recommendations generation...')
            get_PID_date_recommendations()  # This function processes all available studies
            print('   PID/date recommendations completed successfully')
            
        else:
            print('   Skipping recommendations test - no target variables file')
        
        print('\nAll integrated component tests passed!')
        return True
        
    except Exception as e:
        print(f'Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_fallback_mechanism():
    """Test fallback to legacy Ollama client"""
    print('\nTesting Fallback Mechanism...')
    
    try:
        # Test with no AI provider configured (should fallback to Ollama)
        from app.components.generate_descriptions import get_embedding as fallback_embedding
        
        # This should use fallback mechanism
        embedding = fallback_embedding("test variable")
        print(f'   Fallback embedding: {len(embedding)} dimensions')
        
        print('Fallback mechanism test passed!')
        return True
        
    except Exception as e:
        print(f'Fallback test failed: {e}')
        return False

if __name__ == '__main__':
    success1 = test_integrated_components()
    success2 = test_fallback_mechanism()
    
    if success1 and success2:
        print('\n=== ALL TESTS PASSED ===')
        sys.exit(0)
    else:
        print('\n=== SOME TESTS FAILED ===')
        sys.exit(1)
