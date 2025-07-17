import pandas as pd
import fsspec
import time
import ollama
from .util import get_ai_provider, get_ollama_client
from .ai_provider import AIProviderError


results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def return_categorical_prompt(source_var, target_var, initial_instructions, examples, categories):
    prompts = [{"role": "user", "content": """
                                                Given these example values '[0.0, 1.0, nan, nan, nan, nan, nan, nan, nan, nan]'  from the source variable 'ECLAMPSIA'.

                                                I would like to convert them to the target variable 'Eclampsia'  with the following categories: "'yes', 'no'". 

                                                A human has provided these transformation instructions: '0: False, 1:True'. 

                                                Please return a python dictionary to convert the values. the following function will be used:

                                                def generic_catagorical_conversion(x, dictionary_str):
                                                    dictionary_init = eval(dictionary_str)
                                                    dictionary = {str(key): value for key, value in dictionary_init.items()} # convert all keys to string dtype
                                                    x = str(x)
                                                    if x in list(dictionary):
                                                        return dictionary[x]
                                                    else:
                                                        return np.nan

                                                please ensure your output (it will be returned via api) can be directly passed to the function as the dictionary_str argument. 
                                                
                                                The example values are just 10 random values, please ensure the instructions do not truncate or remove items from the dictionary that may not be present in the examples. 
                                                """},
                {"role": "assistant", "content": "{'0.0': 'no', '1.0': 'yes'}"},
                {"role": "user", "content": f"""
                                                Given these example values {examples}  from the source variable {source_var}.

                                                I would like to convert them to the target variable {target_var}  with the following categories: {categories}. 

                                                A human has provided these transformation instructions: {initial_instructions}. 

                                                Please return a python dictionary to convert the values. the following function will be used:

                                                def generic_catagorical_conversion(x, dictionary_str):
                                                    dictionary_init = eval(dictionary_str)
                                                    dictionary = .... # convert all keys to string dtype
                                                    x = str(x)
                                                    if x in list(dictionary):
                                                        return dictionary[x]
                                                    else:
                                                        return np.nan

                                                please ensure your output (it will be returned via api) can be directly passed to the function as the dictionary_str argument. 
                                                
                                                The example values are just 10 random values, please ensure the instructions do not truncate or remove items from the dictionary that may not be present in the examples. 
                                            """}
                ]
    return prompts

def return_direct_conversion_prompt(source_var, target_var, initial_instructions, examples, target_dtype, target_unit, target_example):
    prompts = [{"role": "user", "content": """
                                                Given these example values '[1.9, 1.57, 1.28, 1.67, 1.53, 1.79, 1.71, 1.49, 1.58, 1.49]'  from the source variable 'height (m)'.

                                                I would like to convert them to the target variable 'Height' with the target unit cm and dtype 'float'. An example value is '179.0'

                                                A human has provided these transformation instructions: 'multiply by 10' 

                                                Please return a python commad to convert the values. the command will be passed as x_str to the following funciton:

                                                def generic_direct_conversion(x, x_str, source_dtype, target_dtype):
                                                    x = dtype_conversion(x, source_dtype)
                                                    x = eval(x_str)
                                                    return dtype_conversion(x, source_dtype)

                                                please ensure your output (it will be returned via api) can be directly passed to the function as the x_str argument.
                                                Do not try change the data type in your instructions this is handled within the generic_direct_conversion function. 
                                                If the values should not be mutated return x. If the values need to be multiplied by 10 return x*10. If only the values before a / be preserved return x.split('/')[0]. 
                                                """},
                {"role": "assistant", "content": "x*10"},
                {"role": "user", "content": f"""
                                                Given these example values {examples}  from the source variable {source_var}.

                                                I would like to convert them to the target variable {target_var} with the unit {target_unit} and dtype {target_dtype}. An example value is {target_example}

                                                A human has provided these transformation instructions: {initial_instructions} 

                                                Please return a python commad to convert the values. the command will be passed as x_str to the following funciton:

                                                def generic_direct_conversion(x, x_str, source_dtype, target_dtype):
                                                    x = dtype_conversion(x, source_dtype)
                                                    x = eval(x_str)
                                                    return dtype_conversion(x, source_dtype)

                                                please ensure your output (it will be returned via api) can be directly passed to the function as the x_str argument.
                                                Do not try change the data type in your instructions this is handled within the generic_direct_conversion function. 
                                                If the values should not be mutated return x. If the values need to be multiplied by 10 return x*10. If only the values before a / be preserved return x.split('/')[0]. 
                                            """}
                ]
    return prompts

def get_llm_response(prompt):
    """
    Get the response from the configured AI provider for a given prompt.
    Falls back to Ollama client for backward compatibility.

    Args:
        prompt (list): The prompt messages.

    Returns:
        str: The response from the LLM.
    """
    # Try new AI provider system first
    ai_provider = get_ai_provider()
    if ai_provider:
        try:
            return ai_provider.generate_chat_response(prompt)
        except AIProviderError as e:
            print(f"AI provider chat completion failed: {e}")
            # Fall through to legacy method
    
    # Fallback to legacy Ollama client
    try:
        client = get_ollama_client() or ollama.Client()
        response = client.chat(model='llama3.1:8b', messages=prompt)
        return response['message']['content']
    except Exception as e:
        print(f"Failed to get response from Ollama: {e}")
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

