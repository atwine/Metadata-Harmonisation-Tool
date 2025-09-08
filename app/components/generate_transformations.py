import pandas as pd
import fsspec
import time
import ollama
import streamlit as st
import logging
import os
from .util import get_ai_provider, get_ollama_client, call_with_timeout, retry_with_backoff
from .ai_provider import AIProviderError


results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")
logger = logging.getLogger(__name__)

def _get_prompt_domain() -> str:
    """Select prompt domain via env var PROMPT_DOMAIN; defaults to 'medical'."""
    return os.getenv('PROMPT_DOMAIN', 'medical').strip().lower()


_SYSTEM_TEMPLATES = {
    'medical': (
        "You are a data harmonization assistant for medical/health datasets. "
        "Generate precise, minimal transformations. For direct numeric conversions, "
        "the only allowed operations are arithmetic on variable x using +, -, *, /. "
        "Do not call functions, do not access attributes, do not use power (**) or strings. "
        "Return only a Python expression like 'x/12' or 'x*2' when asked for direct conversions. "
        "For categorical, return a Python dict literal with string keys mapping raw values to target categories."
    ),
    'survey': (
        "You are a data harmonization assistant for survey datasets. Keep outputs simple and robust. "
        "For direct numeric conversions, only arithmetic on x with +, -, *, /. No functions, no attributes, no power (**). "
        "For categorical, return a Python dict literal with string keys (e.g., '1': 'Yes', '0': 'No')."
    ),
}


def _few_shots(domain: str, mode: str) -> list:
    """Return few-shot message pairs for domain and mode ('direct'|'categorical')."""
    if domain == 'survey':
        if mode == 'direct':
            return [
                {"role": "user", "content": "Convert income in thousands to income in units. Examples: [12, 7, 10]"},
                {"role": "assistant", "content": "x*1000"},
                {"role": "user", "content": "Keep age unchanged. Examples: [23, 45, 31]"},
                {"role": "assistant", "content": "x"},
                {"role": "user", "content": "Convert centimeters to meters. Examples: [170, 150, 165]"},
                {"role": "assistant", "content": "x/100"},
                {"role": "user", "content": "Scale satisfaction score (0-10) to percentage."},
                {"role": "assistant", "content": "x*10"},
                {"role": "user", "content": "Convert monthly expense to yearly."},
                {"role": "assistant", "content": "x*12"},
            ]
        else:
            return [
                {"role": "user", "content": "Map response codes to Yes/No: raw values ['1','0','',None]"},
                {"role": "assistant", "content": "{'1': 'Yes', '0': 'No'}"},
                {"role": "user", "content": "Map Likert 1-5 to categories ['Very Low','Low','Neutral','High','Very High']"},
                {"role": "assistant", "content": "{'1':'Very Low','2':'Low','3':'Neutral','4':'High','5':'Very High'}"},
                {"role": "user", "content": "Map gender codes ['M','F','U'] to ['Male','Female']"},
                {"role": "assistant", "content": "{'M':'Male','F':'Female'}"},
                {"role": "user", "content": "Map consent ['Y','N'] to ['Yes','No']"},
                {"role": "assistant", "content": "{'Y':'Yes','N':'No'}"},
                {"role": "user", "content": "Map marital status ['1','2','3'] to ['Single','Married','Other']"},
                {"role": "assistant", "content": "{'1':'Single','2':'Married','3':'Other'}"},
            ]
    else:  # medical default
        if mode == 'direct':
            return [
                {"role": "user", "content": "Convert weight from kg to grams."},
                {"role": "assistant", "content": "x*1000"},
                {"role": "user", "content": "Convert glucose mg/dL to g/L."},
                {"role": "assistant", "content": "x/100"},
                {"role": "user", "content": "Keep heart rate unchanged."},
                {"role": "assistant", "content": "x"},
                {"role": "user", "content": "Convert months to years."},
                {"role": "assistant", "content": "x/12"},
                {"role": "user", "content": "Convert cm to m."},
                {"role": "assistant", "content": "x/100"},
            ]
        else:
            return [
                {"role": "user", "content": "Map diagnosis code ['0','1'] to ['No','Yes']"},
                {"role": "assistant", "content": "{'0':'No','1':'Yes'}"},
                {"role": "user", "content": "Map smoker status ['Y','N'] to ['Yes','No']"},
                {"role": "assistant", "content": "{'Y':'Yes','N':'No'}"},
                {"role": "user", "content": "Map sex ['M','F'] to ['Male','Female']"},
                {"role": "assistant", "content": "{'M':'Male','F':'Female'}"},
                {"role": "user", "content": "Map outcome ['alive','dead'] to standardized ['Alive','Dead']"},
                {"role": "assistant", "content": "{'alive':'Alive','dead':'Dead'}"},
                {"role": "user", "content": "Map binary result ['positive','negative'] to ['Yes','No']"},
                {"role": "assistant", "content": "{'positive':'Yes','negative':'No'}"},
            ]


def return_categorical_prompt(source_var, target_var, initial_instructions, examples, categories):
    domain = _get_prompt_domain()
    sys_msg = _SYSTEM_TEMPLATES.get(domain, _SYSTEM_TEMPLATES['medical'])
    shots = _few_shots(domain, 'categorical')
    core = [{
        "role": "user",
        "content": (
            f"Given example values {examples} from source variable '{source_var}'. "
            f"Convert to target variable '{target_var}' with categories {categories}. "
            f"Human-provided initial instructions: {initial_instructions}. "
            "Return ONLY a Python dict literal with STRING keys mapping raw values to target categories. "
            "Do not include code blocks or explanations."
        )
    }]
    return [{"role": "system", "content": sys_msg}] + shots + core

def return_direct_conversion_prompt(source_var, target_var, initial_instructions, examples, target_dtype, target_unit, target_example):
    domain = _get_prompt_domain()
    sys_msg = _SYSTEM_TEMPLATES.get(domain, _SYSTEM_TEMPLATES['medical'])
    shots = _few_shots(domain, 'direct')
    core = [{
        "role": "user",
        "content": (
            f"Given example values {examples} from source variable '{source_var}'. "
            f"Convert them to target variable '{target_var}' with unit {target_unit} and dtype {target_dtype}. "
            f"An example target value is {target_example}. "
            f"Human-provided initial instructions: {initial_instructions}. "
            "Return ONLY a Python expression using variable x and operators +, -, *, /. "
            "Do not include function calls, string operations, attribute access, or power (**). "
            "Examples: 'x', 'x*100', 'x/12'."
        )
    }]
    return [{"role": "system", "content": sys_msg}] + shots + core

def get_llm_response(prompt):
    """
    Get the response from the configured AI provider for a given prompt.
    Falls back to Ollama client for backward compatibility.

    Args:
        prompt (list): The prompt messages.

    Returns:
        str: The response from the LLM.
    """
    with st.spinner("Generating transformation with AI..."):
        # Try new AI provider system first
        ai_provider = get_ai_provider()
        if ai_provider:
            try:
                return ai_provider.generate_chat_response(prompt)
            except AIProviderError as e:
                # Provide user-friendly feedback in the UI
                try:
                    friendly = ai_provider.handle_provider_error(e)
                except Exception:
                    friendly = str(e)
                st.error(f"LLM error: {friendly} (ERR-LLM-PROVIDER)")
                st.info("Tips: Verify provider credentials and model names, check internet or Ollama status, or increase the request timeout in AI Configuration.")
                logger.error("AI provider chat completion failed", exc_info=True)
                # Fall through to legacy method
        
        # Fallback to legacy Ollama client
        try:
            client = get_ollama_client() or ollama.Client()
            # Use provider-configured timeout if available
            timeout_seconds = 30
            if ai_provider and getattr(ai_provider, 'request_timeout', None):
                timeout_seconds = ai_provider.request_timeout

            def do_chat():
                return client.chat(model='llama3.1:8b', messages=prompt)

            response = retry_with_backoff(lambda: call_with_timeout(do_chat, timeout_seconds))
            return response['message']['content']
        except TimeoutError:
            st.error(f"LLM request timed out after {timeout_seconds}s. (ERR-LLM-TIMEOUT)")
            logger.error("Ollama chat timeout", exc_info=True)
            return None
        except Exception as e:
            st.error(f"Failed to get response from Ollama: {e} (ERR-LLM-OLLAMA)")
            st.info("Tips: Ensure Ollama is running, models are pulled (e.g., llama3.1:8b), and the server URL/port are correct. You may increase timeout in AI Configuration.")
            logger.error("Ollama chat fallback failed", exc_info=True)
            return None
    
def generate_transformations(target_var, source_var, examples, initial_instructions, codebook):
    """
    Generate transformation instructions for converting source variables to target variables.
    Uses the configured AI provider for generating instructions.
    
    Args:
        target_var (str): The target variable name.
        source_var (str): The source variable name.
        examples (list): Example values from the source variable.
        initial_instructions (str): Initial transformation instructions.
        codebook (pd.DataFrame): The codebook containing target variable information.
    
    Returns:
        str: Generated transformation instructions.
    """
    categories = codebook['Categories'].item()
    target_dtype = codebook['dType'].item()
    target_unit = codebook['Unit'].item()
    target_example = codebook['Unit Example'].item()

    if isinstance(categories, str):
        prompts = return_categorical_prompt(source_var, target_var, initial_instructions, examples, categories)
    else:
        prompts = return_direct_conversion_prompt(source_var, target_var, initial_instructions, examples, target_dtype, target_unit, target_example)
    
    return get_llm_response(prompts)

