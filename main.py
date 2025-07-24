# main.py
# To run this backend:
# 1. Install required packages: pip install fastapi uvicorn python-multipart requests
# 2. Run the server: uvicorn main:app --reload

import json
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import requests
import uuid

# --- Configuration ---
# IMPORTANT: Paste your Google AI API Key here.
# Do not share this file publicly with the key included.
API_KEY = "" # <-- PASTE YOUR GOOGLE AI API KEY HERE
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
DB_FILE = "tests.json"

# --- Pydantic Models for Request Bodies ---
class ExamNameRequest(BaseModel):
    examName: str

class TextParseRequest(BaseModel):
    text: str

class SimilarQuestionsRequest(BaseModel):
    questions: List[Dict[str, Any]]

class Test(BaseModel):
    id: str
    title: str
    duration: int
    questions: List[Dict[str, Any]]
    createdAt: str

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Database Helper Functions ---
def load_tests_from_db():
    """Loads all tests from the JSON database file."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_tests_to_db(tests):
    """Saves a list of tests to the JSON database file."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(tests, f, indent=4)
    except IOError as e:
        print(f"Error saving to DB: {e}")

# --- Gemini API Helper Function ---
def call_gemini_api(payload: Dict[str, Any]):
    """
    Calls the Gemini API with a given payload and handles responses.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="Google AI API Key is not set in main.py.")

    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"API call failed: {response.text}")

    result = response.json()
    print("Gemini API raw response:", result)  # Debug print

    if "promptFeedback" in result and "blockReason" in result["promptFeedback"]:
        raise HTTPException(status_code=400, detail=f"Request blocked by API: {result['promptFeedback']['blockReason']}")

    try:
        json_text = result["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(json_text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print("Error parsing Gemini response:", result)
        raise HTTPException(status_code=500, detail=f"Invalid response structure from AI: {e}")

# --- API Endpoints ---

@app.get("/api/tests", response_model=List[Test])
async def get_all_tests():
    """Endpoint to retrieve all saved tests."""
    tests = load_tests_from_db()
    # Sort by creation date, newest first
    tests.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return tests

@app.post("/api/tests")
async def save_new_test(test: Test):
    """Endpoint to save a new test."""
    tests = load_tests_from_db()
    tests.append(test.dict())
    save_tests_to_db(tests)
    return {"status": "success", "test_id": test.id}

@app.delete("/api/tests/{test_id}")
async def delete_a_test(test_id: str):
    """Endpoint to delete a specific test by its ID."""
    tests = load_tests_from_db()
    initial_length = len(tests)
    tests = [t for t in tests if t.get("id") != test_id]
    
    if len(tests) == initial_length:
        raise HTTPException(status_code=404, detail="Test not found")
        
    save_tests_to_db(tests)
    return {"status": "success", "deleted_id": test_id}

@app.post("/api/generate-paper")
async def generate_paper(request: Request):
    """AI endpoint to generate a full test paper from an exam name."""
    data = await request.json()
    exam_name = data.get("examName", "")
    duration = data.get("duration")
    question_count = data.get("questionCount")
    prompt = f"""
    You are an expert exam paper creator. Your task is to generate a complete, realistic mock test based on the provided exam name, matching the real exam's structure as closely as possible.
    Exam Name: "{exam_name}"
    Instructions:
    1. Research and Determine Structure: First, research and determine the standard number of questions for the specified exam.
    2. Generate Exact Question Count: Generate exactly that number of questions. Adhere strictly to the official exam pattern."""
    if question_count:
        prompt += f"\n    2a. Override: Generate exactly {question_count} questions, regardless of the official pattern."
    prompt += """
    3. Create Content: Generate a relevant test title, a suitable duration in minutes based on the official time limit, and the full set of questions."""
    if duration:
        prompt += f"\n    3a. Override: Set the test duration to exactly {duration} minutes."
    prompt += """
    4. Bilingual Questions: For each question and its options, provide both English and a high-quality Hindi translation in the format: "English Text (हिन्दी टेक्स्ट)".
    5. Structure Output: The final output MUST be a single, valid JSON object.
    6. CRITICAL RULE - Each object in the "questions" array MUST have:
       - a non-empty "questionText" (the actual question, not the options or answers),
       - an array of 4 "options",
       - and a "correctOptionIndex".
       The 'questionText' field must contain the full question. Do NOT leave it empty, do NOT repeat the options or answers in this field. If you cannot comply, return an error message in the 'questionText' field.
    7. DOUBLE-CHECK: For each question, ensure that the answer at 'correctOptionIndex' is truly the correct answer for the question and options provided. Do not make mistakes in answer marking. If unsure, return an error message in the 'questionText' field.
    8. For each question, add a brief explanation (in English) of why the correct answer is correct, in an 'explanation' field.
    Generate the full mock test now.
    """
    schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "duration": {"type": "NUMBER"},
            "questions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "questionText": {"type": "STRING"},
                        "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "correctOptionIndex": {"type": "NUMBER"},
                        "explanation": {"type": "STRING"}
                    },
                    "required": ["questionText", "options", "correctOptionIndex", "explanation"]
                }
            }
        },
        "required": ["title", "duration", "questions"]
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}
    result = call_gemini_api(payload)
    # Schema validation: Ensure each question has a non-empty questionText
    warnings = []
    for idx, q in enumerate(result.get("questions", [])):
        # Check questionText
        if not q.get("questionText") or not q["questionText"].strip():
            return {"error": "AI response missing questionText in one or more questions.", "raw_response": result}
        # Check correctOptionIndex is in range
        options = q.get("options", [])
        correct_idx = q.get("correctOptionIndex")
        if not isinstance(correct_idx, int) or correct_idx < 0 or correct_idx >= len(options):
            warnings.append(f"Question {idx+1}: correctOptionIndex {correct_idx} is out of range.")
        # Heuristic: Check if the answer at correctOptionIndex is likely correct (if questionText contains the answer text)
        # This is a best-effort check, not always possible
        if isinstance(correct_idx, int) and 0 <= correct_idx < len(options):
            answer_text = options[correct_idx].split('(')[0].strip().lower()
            if answer_text and answer_text not in q["questionText"].lower():
                # Only warn if the answer is not mentioned at all in the question (very rough check)
                pass  # Optionally, add more sophisticated checks here
    if warnings:
        result["warnings"] = warnings
    return result

@app.post("/api/parse-text")
async def parse_text(request: TextParseRequest):
    """AI endpoint to parse questions from raw text."""
    prompt = f"""
    You are an expert test creation and translation assistant. Analyze the following text.
    Your tasks are:
    1. Extract: Extract the question text, options, and determine the correct answer (marked by '⭕' or '*').
    2. Translate: If content is only in English, translate it to Hindi.
    3. Format: Combine into "English Text (हिन्दी टेक्स्ट)".
    4. Structure: Output a valid JSON array of objects.
    5. Normalize: Ensure exactly 4 options and remove markers like '(A)'.
    Now, parse:
    ---
    {request.text}
    ---
    """
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "questionText": {"type": "STRING"},
                "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                "correctOptionIndex": {"type": "NUMBER"}
            },
            "required": ["questionText", "options", "correctOptionIndex"]
        }
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}
    return call_gemini_api(payload)

@app.post("/api/generate-similar")
async def generate_similar(request: SimilarQuestionsRequest):
    """AI endpoint to generate similar questions based on existing ones."""
    prompt = f"""
    You are an expert question generator. Create a new set of multiple-choice questions similar in topic, style, and difficulty to the provided examples, but not identical.
    Existing Questions (for context):
    {json.dumps(request.questions, indent=2)}
    Instructions:
    1. Analyze: Understand the subject, format, and difficulty.
    2. Generate New Questions: Create the same number of new questions as provided.
    3. Maintain Format: Each new question must be bilingual (English and Hindi) with 4 bilingual options.
    4. Structure Output: The final output MUST be a valid JSON array of question objects.
    5. For each question, add a brief explanation (in English) of why the correct answer is correct, in an 'explanation' field.
    Generate the new, similar questions now.
    """
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "questionText": {"type": "STRING"},
                "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                "correctOptionIndex": {"type": "NUMBER"},
                "explanation": {"type": "STRING"}
            },
            "required": ["questionText", "options", "correctOptionIndex", "explanation"]
        }
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}
    return call_gemini_api(payload)

# --- Serve Frontend ---
# This part serves the index.html file for the root URL.
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# This mounts the current directory to serve static files like CSS or other JS files if needed.
app.mount("/", StaticFiles(directory="."), name="static")

