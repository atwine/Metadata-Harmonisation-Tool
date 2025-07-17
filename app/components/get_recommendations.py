import pandas as pd
import fsspec
from scipy import spatial
from dotenv import dotenv_values
from .util import get_ollama_client, get_ai_provider, OLLAMA_EMBEDDING_MODEL
from .ai_provider import AIProviderError
import numpy as np
import ast

results_path = "results"
input_path = "input"

fs = fsspec.filesystem("")

def get_embedding(text, model=None):
    """
    Generate an embedding for the given text using the configured AI provider.
    Falls back to Ollama client for backward compatibility.
    Ensures the return type is a list or None.
    """
    text = str(text).replace("\n", " ")
    
    # Try new AI provider system first
    ai_provider = get_ai_provider()
    if ai_provider:
        try:
            embedding = ai_provider.generate_embedding(text)
            if isinstance(embedding, list):
                return embedding
            else:
                print(f"Warning: AI provider returned an unexpected format for embedding: {embedding}")
                # Fall through to legacy method
        except AIProviderError as e:
            print(f"Error generating embedding with AI provider: {e}")
            # Fall through to legacy method
    
    # Fallback to legacy Ollama client
    ollama_client = get_ollama_client()
    if not ollama_client:
        print("Error: No AI provider available.")
        return None
    
    try:
        embedding_model = model or OLLAMA_EMBEDDING_MODEL
        response = ollama_client.embeddings(model=embedding_model, prompt=text)
        embedding = response.get('embedding')
        
        if isinstance(embedding, list):
            return embedding
        else:
            print(f"Warning: Ollama returned an unexpected format for embedding: {embedding}")
            return None
            
    except Exception as e:
        print(f"Error generating Ollama embedding for text '{text}': {str(e)}")
        return None

def embed_codebook():
    """
    Embed the codebook variables and descriptions using the configured AI provider.
    """
    if not fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
        df = pd.read_csv(f"{input_path}/target_variables.csv")
        df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(x))
        df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(x))
        df.to_csv(f'{input_path}/target_variables_with_embeddings.csv', index=False)

def embed_study(study):
    """
    Embed the study variables and descriptions using the configured AI provider.

    Args:
        study (str): The study name.
    """
    df = pd.read_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv')[['variable_name','description']]
    df["var_embeddings"] = df['variable_name'].apply(lambda x: get_embedding(x))
    df["description_embeddings"] = df['description'].apply(lambda x: get_embedding(x))
    df.to_csv(f'{input_path}/{study}/dataset_variables_with_embeddings.csv', index=False)

def calculate_cosine_similarity(embedding1, embedding2):
    """
    Calculate the cosine similarity between two embeddings.
    Handles embeddings that might be stored as string representations of lists,
    or are otherwise malformed.
    """
    vec1, vec2 = None, None

    # Process first embedding
    if isinstance(embedding1, str):
        try:
            vec1 = ast.literal_eval(embedding1)
        except (ValueError, SyntaxError):
            pass
    elif isinstance(embedding1, list):
        vec1 = embedding1

    # Process second embedding
    if isinstance(embedding2, str):
        try:
            vec2 = ast.literal_eval(embedding2)
        except (ValueError, SyntaxError):
            pass
    elif isinstance(embedding2, list):
        vec2 = embedding2

    # If either vector is invalid or not a list, return max distance
    if not isinstance(vec1, list) or not isinstance(vec2, list) or not vec1 or not vec2:
        return 1.0  # High distance for invalid inputs

    try:
        # Ensure vectors are 1-D numpy arrays for scipy
        vec1 = np.asarray(vec1, dtype=np.float32).flatten()
        vec2 = np.asarray(vec2, dtype=np.float32).flatten()
        
        if vec1.shape != vec2.shape:
            return 1.0

        similarity = spatial.distance.cosine(vec1, vec2)
        return similarity if np.isfinite(similarity) else 1.0
    except Exception:
        return 1.0

def generate_recommendations(study):
    """
    Generate recommendations for the given study based on cosine similarity of embeddings.

    Args:
        study (str): The study name.
    """
    study_df = pd.read_csv(f'{input_path}/{study}/dataset_variables_with_embeddings.csv')
    target_df = pd.read_csv(f'{input_path}/target_variables_with_embeddings.csv')
    recommendations = []
    distances = []
    for i in range(len(study_df)):
        study_var = study_df['var_embeddings'].iloc[i]
        target_df["var_distance"] = target_df['var_embeddings'].apply(lambda x: calculate_cosine_similarity(study_var, x))
        study_desc = study_df['description_embeddings'].iloc[i]
        target_df["desc_distance"] = target_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(study_desc, x))
        target_df["distance"] = (target_df["desc_distance"] * 0.8) + (target_df["var_distance"] * 0.2)
        target_df = target_df.sort_values("distance")
        recommendations.append(list(target_df.description))
        distances.append(list(target_df.distance))
    study_df['target_recommendations'] = recommendations
    study_df['target_distances'] = distances
    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv', index = False)

def get_embeddings():
    """
    Generate embeddings for all available studies and the codebook.

    This function embeds the codebook and then iterates over all available studies
    to embed their variables and descriptions using the configured AI provider.
    """
    embed_codebook()
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_embeddings.csv'):
            embed_study(study)
        
def get_recommendations():
    """
    Generate recommendations for all available studies.

    This function iterates over all available studies and generates recommendations
    based on the cosine similarity of embeddings.
    """
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_recommendations.csv'):
            generate_recommendations(study)

def generate_PID_date_recommendations(study):
    """
    Generate Index and date recommendations for the given study.

    Args:
        study (str): The study name.
    """
    study_df = pd.read_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv')
    date_recommendations = []
    date_distances = []
    for i in range(len(study_df)):
        study_var = study_df['description'].iloc[i]
        date_embed = get_embedding(f'Date of {study_var}')
        study_df["date_distance"] = study_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(date_embed, x))
        study_df_sorted = study_df.sort_values("date_distance")
        date_recommendations.append(list(study_df_sorted.variable_name))
        date_distances.append(list(study_df_sorted.date_distance))
    study_df['date_recommendations'] = date_recommendations
    study_df['date_distances'] = date_distances

    PID_recommendations = []
    PID_distances = []
    for i in range(len(study_df)):
        study_var = study_df['description'].iloc[i]
        PID_embed = get_embedding(f'Unique Identifier of {study_var}')
        study_df["PID_distance"] = study_df['description_embeddings'].apply(lambda x: calculate_cosine_similarity(PID_embed, x))
        study_df_sorted = study_df.sort_values("PID_distance")
        PID_recommendations.append(list(study_df_sorted.variable_name))
        PID_distances.append(list(study_df_sorted.PID_distance))

    study_df['PID_recommendations'] = PID_recommendations
    study_df['PID_distances'] = PID_distances

    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv', index = False)


def get_PID_date_recommendations():
    """
    Generate PID and date recommendations for all available studies.

    This function iterates over all available studies and generates PID and date
    recommendations based on the cosine similarity of embeddings using the configured AI provider.
    """
    avail_studies = [x for x in fs.ls(f'{input_path}/') if fs.isdir(x)] # get directories
    avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.'] # strip path and remove hidden folders
    for study in avail_studies:
        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'):
            generate_PID_date_recommendations(study)