import streamlit as st
import fsspec
import ollama
import pandas as pd
import ast
from typing import Optional, Callable, Any
from .ai_provider import get_ai_provider_from_session, AIProviderWrapper
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
import re

logger = logging.getLogger(__name__)

# --- Legacy Ollama Configuration (for backward compatibility) ---
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
OLLAMA_CHAT_MODEL = 'llama3.1:8b'
OLLAMA_EMBEDDING_MODEL = 'nomic-embed-text'

# --- Filesystem ---
fs = fsspec.filesystem("")

# --- AI Provider Functions ---
def get_ai_provider() -> Optional[AIProviderWrapper]:
    """
    Get the configured AI provider from session state.
    
    Returns:
        AIProviderWrapper instance or None if not configured
    """
    return get_ai_provider_from_session()

# --- Timeout & Retry Utilities ---
def call_with_timeout(func: Callable[..., Any], timeout_seconds: int, *args, **kwargs) -> Any:
    """
    Execute a callable with a timeout using a thread executor.

    Raises TimeoutError if the function does not return within timeout_seconds.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeout:
            # Cancel if still running to free resources
            future.cancel()
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")


def retry_with_backoff(func: Callable[..., Any], *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs) -> Any:
    """
    Retry a function with exponential backoff on exception.
    """
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                break
    # After exhausting attempts, re-raise last exception
    raise last_exc


def retry(max_attempts: int = 3, base_delay: float = 1.0):
    """
    Decorator to retry a function with exponential backoff.
    """
    def decorator(func: Callable[..., Any]):
        def wrapper(*args, **kwargs):
            return retry_with_backoff(func, *args, max_attempts=max_attempts, base_delay=base_delay, **kwargs)
        return wrapper
    return decorator

def get_ollama_client():
    """
    Legacy function for backward compatibility.
    Returns Ollama client if Ollama is the configured provider.
    
    Returns:
        Ollama client or None
    """
    # Check if we have a configured AI provider
    ai_provider = get_ai_provider()
    if ai_provider and ai_provider.config.provider.value == 'ollama':
        return ai_provider.config.get_client()
    
    # Fallback to legacy behavior
    if 'ollama_client' in st.session_state:
        return st.session_state.ollama_client

    try:
        client = ollama.Client(host=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}")
        response = client.list()

        # Get list of available models
        model_list = response.models

        # Ensure the model list is valid
        if not isinstance(model_list, list) or not model_list:
            st.session_state.ollama_client = None
            return None

        # Extract model names
        available_models = [m.model for m in model_list]
        
        # Check for required models, considering version suffixes
        chat_model_found = False
        embedding_model_found = False
        
        # More flexible matching that handles version suffixes
        for model_name in available_models:
            # Check if model name starts with required model names
            if model_name.startswith(OLLAMA_CHAT_MODEL):
                chat_model_found = True
            if model_name.startswith(OLLAMA_EMBEDDING_MODEL):
                embedding_model_found = True
                
        if chat_model_found and embedding_model_found:
            st.session_state.ollama_client = client
            return client
        else:
            st.session_state.ollama_client = None
            return None

    except Exception as e:
        logger.error(f"Ollama connection error: {str(e)}")
        st.session_state.ollama_client = None
        return None

def delete_files_and_folders(directory_path):
    """
    Delete all files and folders in the specified directory.
    SECURITY: Only allows deletion within whitelisted directories.

    Args:
        directory_path (str): Path to the directory to be cleared.
    """
    # SECURITY: Whitelist of allowed directories for deletion
    allowed_dirs = ['input', 'results', 'preprocess', 'logs']
    
    # SECURITY: Validate path to prevent directory traversal
    try:
        abs_path = Path(directory_path).resolve()
        base_path = Path.cwd().resolve()
        
        # Check if path is within project directory
        if not str(abs_path).startswith(str(base_path)):
            print(f"Security: Blocked path traversal attempt: {directory_path}")
            return
        
        # Check if path is in allowed directories
        rel_path = abs_path.relative_to(base_path)
        if not any(str(rel_path).startswith(allowed) for allowed in allowed_dirs):
            print(f"Security: Deletion not allowed for: {directory_path}")
            return
    except (ValueError, OSError) as e:
        print(f"Security: Invalid path blocked: {directory_path} - {str(e)}")
        return
    
    if fs.exists(directory_path):
        try:
            files_and_dirs = fs.ls(directory_path)
            for item in files_and_dirs:
                try:
                    if fs.isdir(item):
                        fs.rm(item, recursive=True)
                    else:
                        fs.rm(item)
                except Exception as e:
                    # Log the error but continue with other files
                    print(f"Warning: Could not delete {item}: {str(e)}")
                    continue
        except Exception as e:
            # Log the error but don't crash the application
            print(f"Warning: Could not access directory {directory_path}: {str(e)}")

def modify_env(key, value=None, delete=False):
    """
    Modify the .env file to add, update, or delete a key-value pair.
    SECURITY: Validates keys and values to prevent injection attacks.
    """
    # SECURITY: Validate environment variable key format
    if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
        raise ValueError(f"Invalid environment variable key: {key}")
    
    # SECURITY: Validate value doesn't contain newlines (injection risk)
    if value is not None and '\n' in str(value):
        raise ValueError("Environment variable value cannot contain newlines")
    
    if not fs.exists(".env"):
        with open(".env", 'w'):
            pass 
    with open(".env", 'r') as file:
        lines = file.readlines()
    if not delete:
        line_replaced = False
        for i in range(len(lines)):
            # SECURITY: Exact key match to prevent partial matches
            if lines[i].startswith(key + '='):
                lines[i] = key + '=' + str(value) + '\n'
                line_replaced = True
                break
        if not line_replaced:
            lines.append(key + '=' + str(value) + '\n')
    else:
        # SECURITY: Remove only exact key matches
        lines = [line for line in lines if not line.startswith(key + '=')]
    with open(".env", 'w') as file:
        file.writelines(lines)

def safe_literal_eval(val):
    """
    Safely evaluate a string representation of a Python literal (e.g., list).
    Returns an empty list if the input is invalid, NaN, or not a string.
    """
    if pd.isna(val) or not isinstance(val, str):
        return []
    # SECURITY: Validate string length before deserialization to prevent DoS
    if len(val) > 10000:
        return []
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []

# map study utils below
def reorder_lists(list1, list2, value):
    """
    Reorders two lists, such that the value is at the top of list1.
    """
    try:
        index = list1.index(value)
        reordered_list1 = [value] + list1[:index] + list1[index+1:]
        reordered_list2 = [list2[index]] + list2[:index] + list2[index+1:]
        return reordered_list1, reordered_list2
    except ValueError:
        return list1, list2 # Return original lists if value not found

def split_var_confidence(mapped_value):
    """
    Splits a mapped value into variable and confidence parts.
    Precedence is one-space ' - ' (used by pre_process_recomendations), with fallback to two-space '  - '.
    Uses rsplit to avoid breaking when the variable name itself contains ' - '.
    """
    if not isinstance(mapped_value, str):
        return mapped_value, None
    if ' - ' in mapped_value:
        left, right = mapped_value.rsplit(' - ', 1)
        return left, right
    if '  - ' in mapped_value:
        left, right = mapped_value.rsplit('  - ', 1)
        return left, right
    return mapped_value, None
    
def format_example_data(example_data):
    """
    Formats example data for display.
    """
    # PERFORMANCE: Remove redundant list() call
    example_data = [str(x) for x in example_data if pd.notna(x)]
    if len(example_data) >= 5:
        example_data.insert(5, '\n')
    return ' ; '.join(example_data)

def pre_process_recomendations(to_map_df, type_, study):
    """
    Pre-processes recommendations for mapping.
    """
    recommendation_str = to_map_df[f'{type_}_recommendations'].to_list()[0]
    distances_str = to_map_df[f'{type_}_distances'].to_list()[0]

    recommended_codebook = safe_literal_eval(recommendation_str)
    recommended_confidence = safe_literal_eval(distances_str)

    if not recommended_codebook:
        return ['No recommendations available']

    recommended_confidence = [f" - {round((1-x)*(100))}%" for x in recommended_confidence]
    
    if f'{type_}_{study}' in st.session_state and st.session_state[f'{type_}_{study}'] != 'None':
        recommended_codebook, recommended_confidence = reorder_lists(recommended_codebook, recommended_confidence, st.session_state[f'{type_}_{study}'])
    
    recommended_keys = [f"{x}{y}" for x, y in zip(recommended_codebook, recommended_confidence)]
    
    if type_ in ['PID', 'date']:
        recommended_keys.insert(0, 'None  - 0%')
        if f'{type_}_{study}' in st.session_state and st.session_state[f'{type_}_{study}'] != 'None':
            recommended_keys.insert(1, recommended_keys.pop(0))
            
    return recommended_keys

def add_to_session_state(study, patient_id, date):
    """
    Adds patient ID and date to the session state.
    """
    st.session_state[f'PID_{study}'] = patient_id
    st.session_state[f'date_{study}'] = date