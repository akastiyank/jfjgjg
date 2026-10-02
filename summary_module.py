import os
import google.generativeai as genai

def generate_summary(text: str, api_key: str = None) -> str:
    """
    Generates a structured educational summary from input text using Gemini.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is not set. Please configure GEMINI_API_KEY.")
    
    genai.configure(api_key=key)
    
    prompt = (
        "You are EduGenie, a professional educational assistant.\n"
        "Please summarize the following text into a highly structured, easy-to-study summary. "
        "Format the output using Markdown. Include:\n"
        "1. **Core Summary**: A brief, high-level overview of the material (1-2 sentences).\n"
        "2. **Key Concepts & Definitions**: Bold terms and explain them concisely.\n"
        "3. **High-Yield Takeaways**: Use bullet points to highlight the most important facts or formulas.\n\n"
        f"Text to Summarize:\n{text}\n\n"
        "Summary:"
    )
    
    # Use gemini-2.5-flash which is supported in this environment
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating summary with gemini-2.5-flash: {e}")
        return f"Error generating summary: {e}"
