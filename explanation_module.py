import os
import torch
from transformers import pipeline
import google.generativeai as genai

# Cache the pipeline once loaded
_local_pipeline = None

def get_local_pipeline():
    """
    Lazily loads the local LaMini-Flan-T5-783M model pipeline.
    """
    global _local_pipeline
    if _local_pipeline is None:
        print("Loading local LaMini-Flan-T5-783M model pipeline (this may take a few minutes on first run)...")
        model_name = "MBZUAI/LaMini-Flan-T5-783M"
        # Determine device: CUDA GPU if available, else CPU
        device = 0 if torch.cuda.is_available() else -1
        _local_pipeline = pipeline(
            "text2text-generation",
            model=model_name,
            device=device,
            max_length=512
        )
    return _local_pipeline

def explain_concept(concept: str, use_local: bool = True, api_key: str = None) -> str:
    """
    Generate a simplified, beginner-friendly explanation of a concept.
    If use_local is True, it tries to run the local LaMini model.
    If that fails or use_local is False, it falls back to Gemini.
    """
    if use_local:
        try:
            pipe = get_local_pipeline()
            prompt = f"Please write a simple, beginner-friendly explanation of the concept: '{concept}'"
            response = pipe(prompt)
            if response and len(response) > 0:
                return response[0]['generated_text']
            raise ValueError("Empty response from local model")
        except Exception as e:
            print(f"Local LaMini explanation failed: {e}. Falling back to Gemini...")
            # Fallback to Gemini if local model fails
            return explain_concept_with_gemini(concept, api_key)
    else:
        return explain_concept_with_gemini(concept, api_key)

def explain_concept_with_gemini(concept: str, api_key: str = None) -> str:
    """
    Generates a concept explanation using Gemini.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return f"Error: Could not explain '{concept}'. Local model loading failed, and Gemini API Key is not set."
    
    genai.configure(api_key=key)
    prompt = (
        "Explain the following concept in extremely simple, beginner-friendly, and educational terms. "
        "Use analogies if possible and structure the output into 'What it is', 'How it works', and a 'Simple Example'.\n\n"
        f"Concept: {concept}\n\n"
        "Explanation:"
    )
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating explanation via Gemini fallback: {e}"
