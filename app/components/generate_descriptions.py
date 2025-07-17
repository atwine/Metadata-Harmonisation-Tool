import pandas as pd
import math
import fsspec
import time
from pdfminer.high_level import extract_text
import re
from scipy import spatial
from dotenv import dotenv_values
from .util import get_ollama_client, get_ai_provider, OLLAMA_CHAT_MODEL, OLLAMA_EMBEDDING_MODEL
from .ai_provider import AIProviderError

results_path = "results"
input_path = "input"

fs = fsspec.filesystem("")

def get_index(list_in, n, by):
    """
    Get the indices of the top n minimum or maximum values in a list.
    """
    indexed_values = list(enumerate(list_in))
    sorted_values = sorted(indexed_values, key=lambda x: x[1])
    if by == 'min':
        return [index for index, _ in sorted_values[:n]]
    elif by == 'max':
        return [index for index, _ in sorted_values[-n:]]

def return_prompt(init_prompt, variable, context='Not available', example_dict=None):
    """
    Create a prompt for the LLM based on the initial prompt, variable, context, and examples.
    """
    prompts = [{"role": "system", "content": init_prompt},
               {"role": "user", "content": "variable name:  Patient ID, context: 'Not available'"},
               {"role": "assistant", "content": "Patient Identifier (?)"},
               {"role": "user", "content": "variable name:  matdiag, context: 'Not available'"},
               {"role": "assistant", "content": "maternal diagnosis (?)"}]
    if example_dict:
        for example, (example_context, example_description) in example_dict.items():
            prompts.append({"role": "user", "content": f"variable name:  {example}, context: {example_context}"})
            prompts.append({"role": "assistant", "content": example_description})
    prompts.append({"role": "user", "content": f"variable name:  {variable}, context: {context}"})
    return prompts

def convert_pdf_to_txt():
    """
    Convert PDF files to text files for all available studies.
    """
    avail_studies = [f.split('/')[-1] for f in fs.ls(f'{input_path}/') if fs.isdir(f) and not f.split('/')[-1].startswith('.')]
    for study in avail_studies:
        pdf_path = f"{input_path}/{study}/context.pdf"
        txt_path = f"{input_path}/{study}/context.txt"
        if fs.exists(pdf_path) and not fs.exists(txt_path):
            try:
                text = extract_text(pdf_path)
                with fs.open(txt_path, 'w') as of:
                    of.write(text)
            except Exception as e:
                print(f"Error converting {pdf_path}: {e}")

def get_embedding(text, model=None):
    """
    Get the embedding for a given text using the configured AI provider.
    Falls back to Ollama client for backward compatibility.
    """
    text = str(text).replace("\n", " ")
    
    # Try new AI provider system first
    ai_provider = get_ai_provider()
    if ai_provider:
        try:
            return ai_provider.generate_embedding(text)
        except AIProviderError as e:
            print(f"Error generating embedding with AI provider: {e}")
            # Fall through to legacy method
    
    # Fallback to legacy Ollama client
    ollama_client = get_ollama_client()
    if not ollama_client:
        return None
    
    try:
        embedding_model = model or OLLAMA_EMBEDDING_MODEL
        response = ollama_client.embeddings(model=embedding_model, prompt=text)
        return response.get('embedding')
    except Exception as e:
        print(f"Error generating Ollama embedding: {e}")
        return None

def split_text_recursively(text: str, chunk_size: int = 1000) -> list[str]:
    """
    Splits text into chunks of a specified size without breaking words.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    while len(text) > 0:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        
        # Find the last space within the chunk size
        split_pos = text.rfind(' ', 0, chunk_size)
        if split_pos == -1:  # No space found, force split
            split_pos = chunk_size
            
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip() # Remove leading space from next chunk
        
    return chunks

def embed_documents(input_path, study):
    """
    Embed the documents for a given study using the configured AI provider.
    """
    txt_path = f"{input_path}/{study}/context.txt"
    if not fs.exists(txt_path):
        return [], []

    with fs.open(txt_path, 'r') as f:
        text = f.read()
    
    text_chunks = split_text_recursively(text)
    embeddings = [get_embedding(chunk) for chunk in text_chunks]
    return text_chunks, [e for e in embeddings if e is not None]

def get_relevant_context(varname, text_chunks, embeddings, relevance_dist='min'):
    """
    Get the relevant context for a variable name based on embeddings.
    """
    var_embedding = get_embedding(varname)
    if not var_embedding or not embeddings:
        return ''

    distances = [spatial.distance.cosine(var_embedding, x) for x in embeddings]
    if not distances:
        return ''

    context = ''
    if relevance_dist == 'min':
        context = text_chunks[distances.index(min(distances))]
    elif relevance_dist == 'mean':
        top3 = get_index(distances, 3, 'min')
        context = " ".join([text_chunks[i] for i in top3])
    return context

def get_example_dict(described, variables_df, text_chunks=None, embeddings=None):
    """
    Create a dictionary of example contexts and descriptions.
    """
    example_dict = {}
    example_vars = described[:3] # Take the first 3 described variables as examples

    for var in example_vars:
        context = 'Not available'
        if text_chunks and embeddings:
            context = get_relevant_context(var, text_chunks, embeddings)
        description = variables_df[variables_df['variable_name'] == var]['description'].iloc[0]
        example_dict[var] = (context, description)
    return example_dict

def get_llm_response(prompt):
    """
    Get the response from the configured AI provider for a given prompt.
    """
    # Try new AI provider system first
    ai_provider = get_ai_provider()
    if ai_provider:
        try:
            response = ai_provider.generate_chat_response(prompt)
            return f'*{response}'  # Add a * to indicate AI generation
        except AIProviderError as e:
            print(f"AI provider chat completion failed: {e}")
            # Fall through to legacy method
    
    # Fallback to legacy Ollama client
    ollama_client = get_ollama_client()
    if not ollama_client:
        raise ValueError("No AI provider available.")
    
    try:
        response = ollama_client.chat(model=OLLAMA_CHAT_MODEL, messages=prompt)
        label = response['message']['content']
        return f'*{label}'  # Add a * to indicate AI generation
    except Exception as e:
        print(f"Ollama chat completion failed: {e}")
        return None

def generate_descriptions():
    """
    Generate descriptions for variables in datasets.
    """
    config = dotenv_values(".env")
    
    # Check if AI provider is available
    ai_provider = get_ai_provider()
    if not ai_provider:
        # Fallback to legacy Ollama client
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("Could not initialize AI provider. Aborting description generation.")
            return

    init_prompt = config.get('init_prompt', 'Default prompt if not set')
    
    avail_studies = [f.split('/')[-1] for f in fs.ls(f'{input_path}/') if fs.isdir(f) and not f.split('/')[-1].startswith('.')]
    done = {s for s in avail_studies if fs.exists(f'{input_path}/{s}/dataset_variables_auto_completed.csv')}
    avail_studies = [s for s in avail_studies if s not in done]

    for study in avail_studies:
        print(f"Processing study: {study}")
        variables_df = pd.read_csv(f'{input_path}/{study}/dataset_variables.csv')
        
        to_do = variables_df[variables_df['description'].isna()]['variable_name'].tolist()
        described = variables_df[variables_df['description'].notna()]['variable_name'].tolist()

        if not to_do:
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index=False)
            continue

        text_chunks, embeddings = [], []
        if fs.exists(f"{input_path}/{study}/context.txt"):
            text_chunks, embeddings = embed_documents(input_path, study)

        example_dict = get_example_dict(described, variables_df, text_chunks, embeddings) if described else None
        
        codebook = {}
        for var in to_do:
            context = get_relevant_context(var, text_chunks, embeddings) if text_chunks and embeddings else 'Not available'
            prompt = return_prompt(init_prompt, var, context, example_dict)
            llm_response = get_llm_response(prompt)
            if llm_response:
                codebook[var] = llm_response
        
        if codebook:
            for var, desc in codebook.items():
                variables_df.loc[variables_df['variable_name'] == var, 'description'] = desc
            variables_df.to_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv', index=False)

if __name__ == '__main__':
    generate_descriptions()
