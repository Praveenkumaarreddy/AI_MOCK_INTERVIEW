import io
import os
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
        
        # Friendly Initial Prompt
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
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
    """Evaluates the answer and generates a strict scorecard format with emojis."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
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
        return {"response": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI evaluation failed.")
