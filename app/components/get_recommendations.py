import os
import pandas as pd
import fsspec
from scipy import spatial
from dotenv import dotenv_values
from .util import get_ollama_client, get_ai_provider, OLLAMA_EMBEDDING_MODEL
from .ai_provider import AIProviderError
import numpy as np
import ast

# Resolve paths to work for both app runtime (cwd=app/) and tests (cwd=tests/integration)
# Strategy: prefer a local ./input if it exists; otherwise use repo-root /input
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CWD_BASE = os.path.abspath(os.getcwd())
_LOCAL_INPUT = os.path.join(_CWD_BASE, "input")
_LOCAL_RESULTS = os.path.join(_CWD_BASE, "results")
_REPO_INPUT = os.path.join(BASE_DIR, "input")
_REPO_RESULTS = os.path.join(BASE_DIR, "results")
input_path = _LOCAL_INPUT if os.path.exists(_LOCAL_INPUT) else _REPO_INPUT
results_path = _LOCAL_RESULTS if os.path.exists(_LOCAL_RESULTS) else _REPO_RESULTS

fs = fsspec.filesystem("")

# --- Phase 1 perf: small in-process cache to avoid duplicate provider calls in a run ---
_EMBED_CACHE = {}  # key: (provider, model_name_or_default, normalized_text) -> list[float]

def _normalize_text(t):
    """Normalize text consistently before embedding and as dict keys."""
    return str(t).replace("\n", " ")

def get_embedding(text, model=None):
    """
    Generate an embedding for the given text using the configured AI provider.
    Falls back to Ollama client for backward compatibility.
    Ensures the return type is a list or None.
    """
    text = _normalize_text(text)
    # Determine cache key (provider + model + text)
    provider_name = "ollama"
    model_name = model
    ai_provider = get_ai_provider()
    if ai_provider:
        try:
            info = ai_provider.get_provider_info()
            provider_name = info.get("provider", provider_name)
            model_name = model_name or info.get("embedding_model")
        except Exception:
            pass
    key = (provider_name, model_name or "default", text)
    if key in _EMBED_CACHE:
        return _EMBED_CACHE[key]
    
    # Try new AI provider system first
    if ai_provider:
        try:
            embedding = ai_provider.generate_embedding(text)
            if isinstance(embedding, list):
                _EMBED_CACHE[key] = embedding
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
            _EMBED_CACHE[key] = embedding
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
        # Phase 1 perf: deduplicate texts and cache within run
        var_series = df['variable_name'].astype(str).apply(_normalize_text)
        desc_series = df['description'].astype(str).apply(_normalize_text)
        unique_texts = pd.unique(pd.concat([var_series, desc_series], ignore_index=True))
        embed_map = {t: get_embedding(t) for t in unique_texts}
        df["var_embeddings"] = var_series.apply(lambda x: embed_map.get(x))
        df["description_embeddings"] = desc_series.apply(lambda x: embed_map.get(x))
        df.to_csv(f'{input_path}/target_variables_with_embeddings.csv', index=False)

def embed_study(study):
    """
    Embed the study variables and descriptions using the configured AI provider.

    Args:
        study (str): The study name.
    """
    df = pd.read_csv(f'{input_path}/{study}/dataset_variables_auto_completed.csv')[['variable_name','description']]
    # Phase 1 perf: deduplicate texts and cache within run
    var_series = df['variable_name'].astype(str).apply(_normalize_text)
    desc_series = df['description'].astype(str).apply(_normalize_text)
    unique_texts = pd.unique(pd.concat([var_series, desc_series], ignore_index=True))
    embed_map = {t: get_embedding(t) for t in unique_texts}
    df["var_embeddings"] = var_series.apply(lambda x: embed_map.get(x))
    df["description_embeddings"] = desc_series.apply(lambda x: embed_map.get(x))
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

    # Phase 1 perf: parse embeddings once, vectorize cosine distance
    def _to_vec(x):
        if isinstance(x, str):
            # SECURITY: Validate string length before deserialization to prevent DoS
            if len(x) > 100000:  # ~100KB limit for embedding strings
                return None
            # SECURITY: Basic validation - embeddings should look like lists
            if not (x.strip().startswith('[') and x.strip().endswith(']')):
                return None
            try:
                x = ast.literal_eval(x)
            except Exception:
                return None
        return x if isinstance(x, list) else None

    # Parse and build target matrices
    t_var_list = [ _to_vec(v) for v in target_df['var_embeddings'] ]
    t_desc_list = [ _to_vec(v) for v in target_df['description_embeddings'] ]
    # Filter out any None by replacing with empty
    if not t_var_list or not t_desc_list:
        # Fallback: keep old behavior by early return if target embeddings are missing
        target_df['distance'] = 1.0
        study_df['target_recommendations'] = [list(target_df.description)] * len(study_df)
        study_df['target_distances'] = [list(target_df['distance'])] * len(study_df)
        study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv', index=False)
        return

    # Convert to numpy arrays; handle None rows by substituting zeros
    def _list_to_array(lst):
        return np.array(lst, dtype=np.float32) if lst is not None else None

    # Determine embedding dimension from first valid row
    def _first_dim(rows):
        for r in rows:
            arr = _list_to_array(r)
            if arr is not None and arr.ndim == 1 and arr.size > 0:
                return arr.size
        return 0

    dim = min(_first_dim(t_var_list), _first_dim(t_desc_list))
    if dim == 0:
        target_df['distance'] = 1.0
        study_df['target_recommendations'] = [list(target_df.description)] * len(study_df)
        study_df['target_distances'] = [list(target_df['distance'])] * len(study_df)
        study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv', index=False)
        return

    def _pad_or_zero(v):
        arr = _list_to_array(v)
        if arr is None:
            return np.zeros((dim,), dtype=np.float32)
        if arr.ndim != 1:
            return np.zeros((dim,), dtype=np.float32)
        if arr.size != dim:
            # Mismatched dims -> treat as zeros to yield max distance
            return np.zeros((dim,), dtype=np.float32)
        return arr

    T_var = np.stack([_pad_or_zero(v) for v in t_var_list], axis=0)
    T_desc = np.stack([_pad_or_zero(v) for v in t_desc_list], axis=0)

    # L2-normalize targets to compute cosine distance as 1 - dot(u, v)
    def _l2norm(mat):
        denom = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        return mat / denom

    T_var_n = _l2norm(T_var)
    T_desc_n = _l2norm(T_desc)

    recommendations = []
    distances = []

    for i in range(len(study_df)):
        s_var = _to_vec(study_df['var_embeddings'].iloc[i])
        s_desc = _to_vec(study_df['description_embeddings'].iloc[i])

        v_var = _pad_or_zero(s_var)
        v_desc = _pad_or_zero(s_desc)

        # Normalize study vectors
        v_var_n = v_var / (np.linalg.norm(v_var) + 1e-12)
        v_desc_n = v_desc / (np.linalg.norm(v_desc) + 1e-12)

        # Cosine distance = 1 - dot
        d_var = 1.0 - (T_var_n @ v_var_n)
        d_desc = 1.0 - (T_desc_n @ v_desc_n)
        d = (0.8 * d_desc) + (0.2 * d_var)

        # Rank and collect
        idx = np.argsort(d)
        recommendations.append(list(target_df.description.iloc[idx]))
        # Save as plain Python floats to avoid 'np.float32(...)' strings in CSV
        distances.append([float(x) for x in d[idx]])

    study_df['target_recommendations'] = recommendations
    study_df['target_distances'] = distances
    study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_recommendations.csv', index=False)

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

    # Phase 2 perf: vectorize distances over study description embeddings
    def _to_vec(x):
        if isinstance(x, str):
            try:
                x = ast.literal_eval(x)
            except Exception:
                return None
        return x if isinstance(x, list) else None

    # Parse study description embeddings once
    s_desc_list = [ _to_vec(v) for v in study_df['description_embeddings'] ]

    # Determine embedding dimension from first valid row
    def _list_to_array(lst):
        return np.array(lst, dtype=np.float32) if lst is not None else None

    def _first_dim(rows):
        for r in rows:
            arr = _list_to_array(r)
            if arr is not None and arr.ndim == 1 and arr.size > 0:
                return arr.size
        return 0

    dim = _first_dim(s_desc_list)
    if dim == 0:
        # Fallback: empty outputs but preserve columns
        study_df['date_recommendations'] = [[] for _ in range(len(study_df))]
        study_df['date_distances'] = [[] for _ in range(len(study_df))]
        study_df['PID_recommendations'] = [[] for _ in range(len(study_df))]
        study_df['PID_distances'] = [[] for _ in range(len(study_df))]
        study_df.to_csv(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv', index=False)
        return

    def _pad_or_zero(v):
        arr = _list_to_array(v)
        if arr is None or arr.ndim != 1 or arr.size != dim:
            return np.zeros((dim,), dtype=np.float32)
        return arr

    S_desc = np.stack([_pad_or_zero(v) for v in s_desc_list], axis=0)

    # L2-normalize study description embeddings once
    def _l2norm(mat):
        denom = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        return mat / denom

    S_desc_n = _l2norm(S_desc)

    # Pre-embed PID/Date prompt texts with dedup to avoid duplicate provider calls
    desc_series = study_df['description'].astype(str)
    date_texts = desc_series.apply(lambda t: f'Date of {t}')
    pid_texts = desc_series.apply(lambda t: f'Unique Identifier of {t}')
    unique_prompts = pd.unique(pd.concat([date_texts, pid_texts], ignore_index=True))
    prompt_embed_map = {p: get_embedding(p) for p in unique_prompts}

    date_recommendations = []
    date_distances = []
    PID_recommendations = []
    PID_distances = []

    for i in range(len(study_df)):
        # Build query vectors (date and PID) for current description
        q_date = prompt_embed_map.get(date_texts.iloc[i])
        q_pid = prompt_embed_map.get(pid_texts.iloc[i])

        def _norm_vec(v):
            arr = _pad_or_zero(v)
            return arr / (np.linalg.norm(arr) + 1e-12)

        q_date_n = _norm_vec(q_date)
        q_pid_n = _norm_vec(q_pid)

        # Cosine distance = 1 - dot(normalized)
        d_date = 1.0 - (S_desc_n @ q_date_n)
        d_pid = 1.0 - (S_desc_n @ q_pid_n)

        idx_date = np.argsort(d_date)
        idx_pid = np.argsort(d_pid)

        date_recommendations.append(list(study_df.variable_name.iloc[idx_date]))
        # Save distances as plain Python floats to ensure downstream literal_eval works
        date_distances.append([float(x) for x in d_date[idx_date]])
        PID_recommendations.append(list(study_df.variable_name.iloc[idx_pid]))
        PID_distances.append([float(x) for x in d_pid[idx_pid]])

    study_df['date_recommendations'] = date_recommendations
    study_df['date_distances'] = date_distances
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