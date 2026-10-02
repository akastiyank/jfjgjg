import os
import json
import google.generativeai as genai

def generate_learning_path(topic: str, level: str = "Beginner", api_key: str = None) -> dict:
    """
    Generates a structured learning path with recommended steps for a given topic and level.
    Returns a dictionary with keys: Topic, Level, RecommendedTopics (list of strings)
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is not set. Please configure GEMINI_API_KEY.")
    
    genai.configure(api_key=key)
    
    prompt = (
        f"Design a structured, step-by-step learning path for the topic '{topic}' targeting a student at the '{level}' level.\n"
        "The output must be a JSON object containing the following keys exactly:\n"
        "  - 'Topic': the requested topic\n"
        "  - 'Level': the targeted difficulty level ('Beginner', 'Intermediate', or 'Advanced')\n"
        "  - 'RecommendedTopics': a JSON array of strings, where each string represents a specific lesson, subtopic, or milestone to master sequentially (e.g., '1. Intro to Syntax', '2. Functions & Scope'). Provide 5 to 8 steps.\n"
        "Return only the raw JSON. Do not include markdown wraps."
    )
    
    # Use gemini-2.5-flash which is supported in this environment
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"Error generating learning path with gemini-2.5-flash: {e}")
        # Mock learning path in case of complete API failure
        return {
            "Topic": topic,
            "Level": level,
            "RecommendedTopics": [
                f"1. Foundations of {topic}",
                f"2. Core Concepts and Principles of {topic}",
                f"3. Practical Applications of {topic}",
                f"4. Intermediate Workflows with {topic}",
                f"5. Advanced Best Practices for {topic}"
            ]
        }
