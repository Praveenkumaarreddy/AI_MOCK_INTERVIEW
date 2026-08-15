import io
import os
import sqlite3
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pypdf
import google.generativeai as genai

app = FastAPI(title="Friendly AI Interview Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- DATABASE SETUP ---
DB_NAME = "interview_history.db"

def init_db():
    """Creates the database table if it doesn't exist yet."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            resume_snippet TEXT,
            transcript TEXT,
            feedback TEXT,
            confidence_score INTEGER,
            technical_score INTEGER,
            communication_score INTEGER,
            next_question TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run database setup immediately when the server starts
init_db()

def save_to_database(resume_text, transcript, raw_ai_text):
    """Parses the AI output and logs the scores to the database."""
    try:
        # Extract scores using Regex
        conf_match = re.search(r"Confidence:\s*(\d+)", raw_ai_text, re.IGNORECASE)
        tech_match = re.search(r"Technical:\s*(\d+)", raw_ai_text, re.IGNORECASE)
        comm_match = re.search(r"Communication:\s*(\d+)", raw_ai_text, re.IGNORECASE)
        feed_match = re.search(r"Feedback:\s*(.+)", raw_ai_text, re.IGNORECASE)
        next_match = re.search(r"Next Question:\s*(.+)", raw_ai_text, re.IGNORECASE)

        conf_score = int(conf_match.group(1)) if conf_match else None
        tech_score = int(tech_match.group(1)) if tech_match else None
        comm_score = int(comm_match.group(1)) if comm_match else None
        feedback = feed_match.group(1) if feed_match else "N/A"
        next_q = next_match.group(1) if next_match else "N/A"

        # Connect to DB and insert the row
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluations (
                timestamp, resume_snippet, transcript, feedback, 
                confidence_score, technical_score, communication_score, next_question
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            resume_text[:500], # Save first 500 chars of resume
            transcript,
            feedback,
            conf_score,
            tech_score,
            comm_score,
            next_q
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database logging error: {e}")

class InterviewRequest(BaseModel):
    transcript: str
    resume_text: str

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Extracts text from PDF and generates a friendly emoji greeting."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF format is supported.")
    
    try:
        content = await file.read()
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        extracted_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages if page.extract_text()])
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="PDF contains no readable text.")
        
        model = genai.GenerativeModel("gemini-3.6-flash")
        intro_prompt = (
            "You are a super friendly, encouraging AI recruiter. Read this candidate's resume and generate a short, "
            "warm welcome message with emojis. Then, ask your very first interview question based on their coolest project or skill.\n\n"
            f"Resume:\n{extracted_text[:2500]}"
        )
        
        greeting = model.generate_content(intro_prompt).text.strip()
        
        return {
            "status": "success",
            "resume_text": extracted_text.strip(),
            "initial_question": greeting
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Parsing Failed: {str(e)}")

@app.post("/evaluate")
async def process_interview(request: InterviewRequest):
    """Evaluates the answer, saves it to the database, and returns the scorecard."""
    try:
        model = genai.GenerativeModel("gemini-3.6-flash")
        
        prompt = (
            "You are a highly supportive, friendly AI technical interviewer. Use emojis naturally! 🌟\n"
            f"Candidate's Resume Context:\n{request.resume_text[:2000]}\n\n"
            "Evaluate the candidate's spoken answer. You MUST format your response EXACTLY like this template below. Do not use asterisks or markdown styling for the headers:\n\n"
            "Feedback: [Your warm, encouraging feedback using emojis]\n"
            "Suggestion: [One specific, highly actionable tip to improve their answer]\n"
            "Confidence: [Score 1-10]\n"
            "Technical: [Score 1-10]\n"
            "Communication: [Score 1-10]\n"
            "Next Question: [Your next friendly question based on their resume and previous answer]\n\n"
            f"Candidate's Answer:\n\"{request.transcript}\""
        )
        
        response = model.generate_content(prompt)
        
        # FIXED: Call the database function to log this evaluation
        save_to_database(request.resume_text, request.transcript, response.text)
        
        return {"response": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI evaluation failed.")

# --- NEW ENDPOINT TO SHOW JUDGES ---
@app.get("/history")
def get_interview_history():
    """Endpoint for judges to see the live database records."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Fetch the 10 most recent interview evaluations
        cursor.execute("SELECT * FROM evaluations ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        return {"total_records": len(rows), "records": [dict(row) for row in rows]}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
