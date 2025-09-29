import ollama
import traceback

def debug_ollama_connection():
    """Debug Ollama connection step by step with full error reporting"""
    results = []
    
    # Step 1: Initialize client
    try:
        print("1. Creating Ollama client...")
        client = ollama.Client(host="http://localhost:11434")
        results.append("[SUCCESS] Client created successfully")
    except Exception as e:
        results.append(f"[FAIL] Client creation failed: {type(e).__name__}: {str(e)}")
        results.append(traceback.format_exc())
        return results
    
    # Step 2: Get list response
    try:
        print("2. Calling client.list()...")
        response = client.list()
        results.append(f"[SUCCESS] client.list() returned object")
        results.append(f"[SUCCESS] Response type: {type(response).__name__}")
        
        # Try to access raw response contents
        try:
            results.append(f"Raw response: {response}")
        except:
            results.append("Could not print raw response")
            
        # Examine all public attributes
        results.append("Examining response attributes:")
        for attr in dir(response):
            if not attr.startswith('_'):  # Skip private attributes
                try:
                    attr_value = getattr(response, attr)
                    results.append(f"  - {attr}: {type(attr_value).__name__}")
                except Exception as e:
                    results.append(f"  - {attr}: ERROR accessing: {str(e)}")
    except Exception as e:
        results.append(f"[FAIL] client.list() failed: {type(e).__name__}: {str(e)}")
        results.append(traceback.format_exc())
        return results
    
    # Step 3: Check for models attribute
    try:
        print("3. Testing different ways to access models...")
        
        # Test attribute access
        results.append("A. Testing attribute access (response.models):")
        if hasattr(response, 'models'):
            try:
                models = response.models
                results.append(f"[SUCCESS] Found models attribute: {type(models).__name__}")
                results.append(f"Number of models: {len(models) if models else 0}")
                
                if models and len(models) > 0:
                    model = models[0]
                    results.append(f"First model type: {type(model).__name__}")
                    results.append("First model attributes:")
                    
                    for attr in dir(model):
                        if not attr.startswith('_'):
                            try:
                                attr_value = getattr(model, attr)
                                results.append(f"  * {attr}: {attr_value}")
                            except Exception as e:
                                results.append(f"  * {attr}: ERROR accessing: {str(e)}")
            except Exception as e:
                results.append(f"[FAIL] Error accessing models attribute: {type(e).__name__}: {str(e)}")
        else:
            results.append("[FAIL] No models attribute found")
            
        # Test dictionary access
        results.append("B. Testing dictionary access (response['models']):")
        try:
            models = response['models']
            results.append(f"[SUCCESS] Dictionary access worked: {type(models).__name__}")
            results.append(f"Number of models: {len(models) if models else 0}")
        except Exception as e:
            results.append(f"[FAIL] Dictionary access failed: {type(e).__name__}: {str(e)}")
            
        # Test .get() method
        results.append("C. Testing .get() method (response.get('models')):")
        if hasattr(response, 'get'):
            try:
                models = response.get('models')
                results.append(f"[SUCCESS] .get() method worked: {type(models).__name__}")
                results.append(f"Number of models: {len(models) if models else 0}")
            except Exception as e:
                results.append(f"[FAIL] .get() method failed: {type(e).__name__}: {str(e)}")
        else:
            results.append("[FAIL] No .get() method found")
            
    except Exception as e:
        results.append(f"[FAIL] Testing access methods failed: {type(e).__name__}: {str(e)}")
        results.append(traceback.format_exc())
    
    # Step 4: List available models in different ways
    try:
        print("4. Attempting to list available models...")
        
        # Different ways to get model names
        results.append("Extracting model names using different methods:")
        
        # Try attribute access to models first
        try:
            models = getattr(response, 'models', None)
            if models:
                results.append("A. Using attribute access to models:")
                
                # Try .model attribute on each model object
                try:
                    model_names_attr = [getattr(m, 'model', None) for m in models]
                    results.append(f"[SUCCESS] Model names via .model attribute: {model_names_attr}")
                except Exception as e:
                    results.append(f"[FAIL] Accessing .model attribute failed: {str(e)}")
                
                # Try ['model'] dict access on each model object
                try:
                    model_names_dict = [m['model'] if 'model' in m else None for m in models]
                    results.append(f"[SUCCESS] Model names via ['model'] access: {model_names_dict}")
                except Exception as e:
                    results.append(f"[FAIL] Dictionary ['model'] access failed: {str(e)}")
                    
                # Try .get('model') on each model object    
                try:
                    if hasattr(models[0], 'get'):
                        model_names_get = [m.get('model') for m in models]
                        results.append(f"[SUCCESS] Model names via .get('model'): {model_names_get}")
                    else:
                        results.append("[FAIL] Model objects don't have .get() method")
                except Exception as e:
                    results.append(f"[FAIL] Using .get('model') failed: {str(e)}")
                    
                # Try examining string representation
                try:
                    for i, m in enumerate(models[:2]):  # Just show first two
                        results.append(f"Model {i} string representation: {str(m)}")
                except Exception as e:
                    results.append(f"[FAIL] Getting string representation failed: {str(e)}")
        except Exception as e:
            results.append(f"[FAIL] Error working with models list: {str(e)}")
    except Exception as e:
        results.append(f"[FAIL] Listing models failed: {type(e).__name__}: {str(e)}")
        results.append(traceback.format_exc())

    return results

if __name__ == '__main__':
    print("=== Ollama Connection Diagnostic Tool ===")
    print("This script will attempt to connect to Ollama and diagnose any issues")
    print("====================================\n")
    
    results = debug_ollama_connection()
    print("\n=== DIAGNOSTIC RESULTS ===")
    for line in results:
        print(line)
