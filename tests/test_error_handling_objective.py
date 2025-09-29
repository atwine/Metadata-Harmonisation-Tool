#!/usr/bin/env python3
"""
Minimal tests for timeout/retry/error messaging integration without external providers.
"""
import sys
import time
sys.path.append('.')

import streamlit as st  # noqa: F401 (ensures st.error calls don't crash)

# Test generate_transformations.get_llm_response fallback retry logic
from app.components import generate_transformations as gt
import ollama


class FakeFailClient:
    def __init__(self, *args, **kwargs):
        pass
    def chat(self, *args, **kwargs):
        # Simulate immediate failure to exercise retry logic
        raise RuntimeError("Simulated chat failure")


def test_generate_transformations_retry_and_error():
    # Ensure no AI provider in session so fallback path is used
    if 'ai_config' in st.session_state:
        del st.session_state['ai_config']

    # Monkey-patch ollama.Client to our failing client
    original_client = ollama.Client
    ollama.Client = FakeFailClient
    try:
        prompt = [{"role": "user", "content": "hello"}]
        result = gt.get_llm_response(prompt)
        # Should return None after retries, not raise
        assert result is None
        print('OK: generate_transformations fallback retry/error handling')
    finally:
        ollama.Client = original_client


if __name__ == '__main__':
    test_generate_transformations_retry_and_error()
    print('All error handling objective tests passed.')
