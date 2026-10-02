import os
import json
import uuid
import hashlib
from datetime import datetime
from threading import Lock
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

# Import our AI modules
from qna import generate_answer
from explanation_module import explain_concept
from quiz_module import generate_quiz
from summary_module import generate_summary
from learning_path import generate_learning_path

# Load environment variables if .env file exists
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="EduGenie",
    description="Intelligent AI-powered educational assistant designed to enhance learning."
)

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Database file setup
DB_FILE = os.path.join(BASE_DIR, "database.json")
db_lock = Lock()

def init_db():
    if not os.path.exists(DB_FILE):
        with db_lock:
            with open(DB_FILE, "w") as f:
                json.dump({
                    "users": [],
                    "queries": [],
                    "responses": [],
                    "learning_paths": [],
                    "quizzes": [],
                    "summaries": []
                }, f, indent=2)

def read_db():
    init_db()
    with db_lock:
        with open(DB_FILE, "r") as f:
            return json.load(f)

def write_db(data):
    with db_lock:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)

# Hashing utility
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Dependencies
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized session. Please login.")
    token = authorization.split(" ")[1]
    db = read_db()
    for user in db["users"]:
        if user["UserID"] == token:
            return user
    raise HTTPException(status_code=401, detail="Session expired or invalid. Please login again.")

# API Key helper
def get_gemini_key(x_gemini_key: Optional[str] = Header(None)) -> str:
    key = x_gemini_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is missing. Please set it in the environment variable GEMINI_API_KEY or provide the X-Gemini-Key header."
        )
    return key

# Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class QnaPayload(BaseModel):
    question: str

class ExplainPayload(BaseModel):
    concept: str
    use_local: bool = True

class QuizPayload(BaseModel):
    topic: str
    num_questions: int = 5

class SummaryPayload(BaseModel):
    text: str

class LearningPathPayload(BaseModel):
    topic: str
    level: str = "Beginner"

# HTML Page Route
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# Auth Endpoints
@app.post("/api/auth/register")
def register(payload: UserRegister):
    db = read_db()
    for user in db["users"]:
        if user["Email"].lower() == payload.email.lower():
            raise HTTPException(status_code=400, detail="Email is already registered.")
            
    user_id = str(uuid.uuid4())
    new_user = {
        "UserID": user_id,
        "UserName": payload.username,
        "Email": payload.email.lower(),
        "PasswordHash": hash_password(payload.password),
        "CreatedAt": datetime.utcnow().isoformat()
    }
    db["users"].append(new_user)
    write_db(db)
    return {"message": "Registration successful!", "user_id": user_id, "username": payload.username}

@app.post("/api/auth/login")
def login(payload: UserLogin):
    db = read_db()
    pwd_hash = hash_password(payload.password)
    for user in db["users"]:
        if user["Email"].lower() == payload.email.lower() and user["PasswordHash"] == pwd_hash:
            return {
                "message": "Login successful!",
                "token": user["UserID"],
                "username": user["UserName"],
                "email": user["Email"]
            }
    raise HTTPException(status_code=401, detail="Invalid email or password.")

# Educational Endpoints
@app.post("/api/qna")
def api_qna(payload: QnaPayload, user: dict = Depends(get_current_user), api_key: str = Depends(get_gemini_key)):
    db = read_db()
    query_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Generate Answer
    try:
        answer_text = generate_answer(payload.question, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")
    
    # Save Query
    query = {
        "QueryID": query_id,
        "UserID": user["UserID"],
        "QueryType": "qa",
        "QueryText": payload.question,
        "CreatedAt": now
    }
    db["queries"].append(query)
    
    # Save Response
    response = {
        "ResponseID": response_id,
        "QueryID": query_id,
        "ResponseText": answer_text,
        "ModelUsed": "Gemini 1.5 Pro",
        "CreatedAt": now
    }
    db["responses"].append(response)
    
    write_db(db)
    return {"query_id": query_id, "response_id": response_id, "answer": answer_text}

@app.post("/api/explain")
def api_explain(payload: ExplainPayload, user: dict = Depends(get_current_user), api_key: str = Depends(get_gemini_key)):
    db = read_db()
    query_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Generate Explanation
    try:
        # Pass the key. Gemini will be used as a fallback if use_local fails or if it's set to False
        explanation_text = explain_concept(payload.concept, use_local=payload.use_local, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")
    
    model_used = "LaMini-Flan-T5-783M (Local)" if payload.use_local else "Gemini 1.5 Flash"
    # Just in case local failed and fell back
    if "Gemini fallback" in explanation_text or "Could not explain" in explanation_text:
        model_used = "Gemini 1.5 Flash (Fallback)"
        
    query = {
        "QueryID": query_id,
        "UserID": user["UserID"],
        "QueryType": "explain",
        "QueryText": payload.concept,
        "CreatedAt": now
    }
    db["queries"].append(query)
    
    response = {
        "ResponseID": response_id,
        "QueryID": query_id,
        "ResponseText": explanation_text,
        "ModelUsed": model_used,
        "CreatedAt": now
    }
    db["responses"].append(response)
    
    write_db(db)
    return {"query_id": query_id, "response_id": response_id, "explanation": explanation_text, "model": model_used}

@app.post("/api/quiz")
def api_quiz(payload: QuizPayload, user: dict = Depends(get_current_user), api_key: str = Depends(get_gemini_key)):
    db = read_db()
    query_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Generate Quiz MCQs
    try:
        questions = generate_quiz(payload.topic, num_questions=payload.num_questions, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")
    
    query = {
        "QueryID": query_id,
        "UserID": user["UserID"],
        "QueryType": "quiz",
        "QueryText": payload.topic,
        "CreatedAt": now
    }
    db["queries"].append(query)
    
    response = {
        "ResponseID": response_id,
        "QueryID": query_id,
        "ResponseText": f"Generated interactive quiz with {len(questions)} questions.",
        "ModelUsed": "Gemini 1.5 Pro",
        "CreatedAt": now
    }
    db["responses"].append(response)
    
    # Save individual quiz questions
    saved_questions = []
    for q in questions:
        quiz_item = {
            "QuizID": str(uuid.uuid4()),
            "QueryID": query_id,
            "QuestionText": q.get("QuestionText"),
            "OptionA": q.get("OptionA"),
            "OptionB": q.get("OptionB"),
            "OptionC": q.get("OptionC"),
            "OptionD": q.get("OptionD"),
            "CorrectOption": q.get("CorrectOption"),
            "CreatedAt": now
        }
        db["quizzes"].append(quiz_item)
        saved_questions.append(quiz_item)
        
    write_db(db)
    return {"query_id": query_id, "response_id": response_id, "questions": saved_questions}

@app.post("/api/summary")
def api_summary(payload: SummaryPayload, user: dict = Depends(get_current_user), api_key: str = Depends(get_gemini_key)):
    db = read_db()
    query_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Generate summary
    try:
        summary_text = generate_summary(payload.text, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")
        
    query = {
        "QueryID": query_id,
        "UserID": user["UserID"],
        "QueryType": "summarize",
        "QueryText": payload.text[:100] + "...", # Store preview of original text
        "CreatedAt": now
    }
    db["queries"].append(query)
    
    response = {
        "ResponseID": response_id,
        "QueryID": query_id,
        "ResponseText": summary_text,
        "ModelUsed": "Gemini 1.5 Pro",
        "CreatedAt": now
    }
    db["responses"].append(response)
    
    # Save detailed summary record
    summary_item = {
        "SummaryID": str(uuid.uuid4()),
        "QueryID": query_id,
        "OriginalText": payload.text,
        "SummaryText": summary_text,
        "ModelUsed": "Gemini 1.5 Pro",
        "CreatedAt": now
    }
    db["summaries"].append(summary_item)
    
    write_db(db)
    return {"query_id": query_id, "response_id": response_id, "summary": summary_text}

@app.post("/api/learning-path")
def api_learning_path(payload: LearningPathPayload, user: dict = Depends(get_current_user), api_key: str = Depends(get_gemini_key)):
    db = read_db()
    query_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Generate learning path
    try:
        path_data = generate_learning_path(payload.topic, level=payload.level, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate learning path: {str(e)}")
        
    query = {
        "QueryID": query_id,
        "UserID": user["UserID"],
        "QueryType": "learn",
        "QueryText": f"Topic: {payload.topic} | Level: {payload.level}",
        "CreatedAt": now
    }
    db["queries"].append(query)
    
    rec_topics = path_data.get("RecommendedTopics", [])
    response_text = f"Learning Path: {', '.join(rec_topics)}"
    response = {
        "ResponseID": response_id,
        "QueryID": query_id,
        "ResponseText": response_text,
        "ModelUsed": "Gemini 1.5 Pro",
        "CreatedAt": now
    }
    db["responses"].append(response)
    
    # Save detailed learning path record
    path_item = {
        "PathID": str(uuid.uuid4()),
        "QueryID": query_id,
        "Topic": path_data.get("Topic", payload.topic),
        "Level": path_data.get("Level", payload.level),
        "RecommendedTopics": rec_topics,
        "CreatedAt": now
    }
    db["learning_paths"].append(path_item)
    
    write_db(db)
    return {"query_id": query_id, "response_id": response_id, "learning_path": path_item}

# History retrieve endpoint
@app.get("/api/history")
def api_history(user: dict = Depends(get_current_user)):
    db = read_db()
    user_queries = [q for q in db["queries"] if q["UserID"] == user["UserID"]]
    
    history_list = []
    for q in user_queries:
        qid = q["QueryID"]
        resp = next((r for r in db["responses"] if r["QueryID"] == qid), None)
        
        detail = None
        if q["QueryType"] == "learn":
            detail = next((p for p in db["learning_paths"] if p["QueryID"] == qid), None)
        elif q["QueryType"] == "quiz":
            detail = [qz for qz in db["quizzes"] if qz["QueryID"] == qid]
        elif q["QueryType"] == "summarize":
            detail = next((s for s in db["summaries"] if s["QueryID"] == qid), None)
            
        history_list.append({
            "QueryID": q["QueryID"],
            "QueryType": q["QueryType"],
            "QueryText": q["QueryText"],
            "CreatedAt": q["CreatedAt"],
            "ResponseText": resp["ResponseText"] if resp else "No response generated.",
            "ModelUsed": resp["ModelUsed"] if resp else "N/A",
            "Detail": detail
        })
        
    # Sort descending by CreatedAt
    history_list.sort(key=lambda x: x["CreatedAt"], reverse=True)
    return history_list
