import os
import google.generativeai as genai

def generate_answer(question: str, api_key: str = None) -> str:
    """
    Generate an answer to a user's academic question using Gemini 1.5 Pro (with fallback to 1.5 Flash).
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is not set. Please configure GEMINI_API_KEY.")
    
    genai.configure(api_key=key)
    
    prompt = (
        "You are EduGenie, a friendly, intelligent educational assistant.\n"
        "Please answer the student's question in a clear, structured, and pedagogical manner. "
        "Use rich formatting, bold words for key terms, bullet points, and code blocks (with language specified) "
        "or mathematical expressions where helpful.\n\n"
        f"Question: {question}\n\n"
        "Detailed Answer:"
    )
    
    # Use gemini-2.5-flash which is supported in this environment
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating answer with gemini-2.5-flash: {e}")
        return f"Sorry, I encountered an error while generating the answer: {e}"
