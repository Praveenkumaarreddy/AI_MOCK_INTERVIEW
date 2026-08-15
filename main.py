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

# --- ROOT HEALTH CHECK ROUTE ---
@app.get("/")
def root():
    """Prevents 404 errors on Render health checks."""
    return {"status": "online", "message": "AI Interview Coach Backend is running!"}

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Extracts text from PDF and generates a concise, direct welcome message."""
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
            "You are a professional AI technical interviewer. "
            "Keep your greeting strictly to 1 short sentence, and immediately ask ONE clear, direct technical question based on their resume. No markdown asterisks or bullet points.\n\n"
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
            "You are a highly supportive, friendly, and professional AI technical interviewer. "
            "Use emojis naturally and sparingly. 🌟\n\n"
            "Your job is to evaluate the candidate's spoken answer based on the resume context "
            "and the question being answered. Be fair, concise, and constructive.\n\n"
            f"Candidate's Resume Context:\n{request.resume_text[:4000]}\n\n"
            "STRICT OUTPUT RULES:\n"
            "- Follow the exact format below.\n"
            "- Do not add any text before or after the format.\n"
            "- Do not use markdown, asterisks, bullets, or headings.\n"
            "- Every score must be an integer from 1 to 10.\n"
            "- Feedback must be under 2 short sentences.\n"
            "- Suggestion must contain exactly one specific, actionable improvement.\n"
            "- Next Question must be conversational and under 15 words.\n"
            "- Technical score should evaluate technical correctness, not speaking ability.\n"
            "- Communication score should evaluate clarity, structure, confidence, and fluency.\n"
            "- Confidence score should reflect how confidently and convincingly the candidate answered.\n"
            "- If the question is not technical, still score Technical based on the relevance "
            "and accuracy of any technical content provided.\n\n"
            "REQUIRED FORMAT:\n"
            "Feedback: [Short, warm evaluation]\n"
            "Suggestion: [One specific actionable tip]\n"
            "Confidence: [Integer 1-10]\n"
            "Technical: [Integer 1-10]\n"
            "Communication: [Integer 1-10]\n"
            "Next Question: [Short conversational question]\n\n"
            f"Candidate's Answer:\n\"{request.transcript}\""
        )
        
        response = model.generate_content(prompt)
        
        # Save evaluation to SQLite database
        save_to_database(request.resume_text, request.transcript, response.text)
        
        return {"response": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI evaluation failed.")

# --- ENDPOINT TO SHOW JUDGES ---
@app.get("/history")
def get_interview_history():
    """Endpoint for judges to see the live database records."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evaluations ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        return {"total_records": len(rows), "records": [dict(row) for row in rows]}
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
