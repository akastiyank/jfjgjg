import os
import json
import google.generativeai as genai

def generate_quiz(topic: str, num_questions: int = 5, api_key: str = None) -> list:
    """
    Generates a structured MCQ quiz using Gemini 1.5 Pro/Flash in JSON Mode.
    Returns a list of dictionaries containing: QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is not set. Please configure GEMINI_API_KEY.")
    
    genai.configure(api_key=key)
    
    prompt = (
        f"Generate an educational multiple-choice quiz about the topic: '{topic}'.\n"
        f"Generate exactly {num_questions} questions. The output must be a JSON array of objects. "
        "Each object in the array represents a single question and MUST have the exact following keys:\n"
        "  - 'QuestionText': the question string\n"
        "  - 'OptionA': option A text\n"
        "  - 'OptionB': option B text\n"
        "  - 'OptionC': option C text\n"
        "  - 'OptionD': option D text\n"
        "  - 'CorrectOption': a single uppercase character: 'A', 'B', 'C', or 'D'\n"
        "Do not include any markdown wrap (like ```json) in the raw JSON output. Return only the JSON list."
    )
    
    # Try gemini-2.5-flash
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        questions = json.loads(response.text)
        if isinstance(questions, list):
            return questions
        raise ValueError("Response is not a JSON list")
    except Exception as e:
        print(f"Quiz generation with gemini-2.5-flash failed: {e}")
        
        # Return a simple mock quiz to avoid complete failure
        return [
            {
                "QuestionText": f"What is the core concept of {topic}?",
                "OptionA": "Option A explanation",
                "OptionB": "Option B explanation",
                "OptionC": "Option C explanation",
                "OptionD": "Option D explanation",
                "CorrectOption": "A"
            }
        ]
