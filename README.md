# AI_MOCK_INTERVIEW
# ✨ Friendly AI Interview Coach

**Live Demo:** [ai-mock-interview-blue-two.vercel.app](https://ai-mock-interview-blue-two.vercel.app)

A modern, full-stack AI mock interview platform designed to provide highly personalized, resume-driven technical and behavioral practice. The application utilizes a decoupled architecture to process real-time speech and dynamically evaluate candidates using Google's latest Gemini 3.6 Flash model.

## ⚙️ System Architecture

*   **Frontend (Client):** Hosted on **Vercel**. Built with pure HTML, CSS, and Vanilla JavaScript. Features a responsive UI, webcam integration, and utilizes the native Web Speech API (optimized for `en-IN` accents) for seamless real-time audio transcription.
*   **Backend (API):** Hosted on **Render**. A high-speed REST API engineered with **Python & FastAPI**. Securely handles cross-origin requests (CORS), file uploads, and heavy data processing.
*   **AI Engine:** Powered by **Google Gemini 3.6 Flash**. The backend utilizes strict prompt engineering to force structured JSON-like outputs, giving the AI a friendly, encouraging personality while delivering precise scoring metrics.

## ⚡ Key Features

*   **📄 Dynamic Resume Parsing:** Users upload their PDF resume, which is parsed backend-side using `pypdf`. The AI reads the extracted text and tailors its initial greeting and interview questions to the candidate's actual project history and skills.
*   **🎙️ Real-Time Speech-to-Text:** Captures the candidate's spoken answers directly through the browser, bypassing mobile event-bubbling bugs for a smooth cross-device experience.
*   **📊 Instant AI Scorecard:** The AI strictly evaluates each answer and returns actionable feedback, a "Pro Tip" suggestion, and numerical scores (1-10) for:
    *   Confidence
    *   Technical Accuracy
    *   Communication Skills

## 🛠️ Tech Stack

*   **Languages:** Python 3.10+, JavaScript, HTML5, CSS3
*   **Backend Framework:** FastAPI, Pydantic, Uvicorn
*   **AI/LLM:** Google Generative AI SDK (`gemini-3.6-flash`)
*   **File Processing:** `python-multipart`, `pypdf`
*   **Deployment Integration:** Vercel (Frontend), Render (Backend API)

## 💻 Local Setup & Installation

To run the backend API locally for development:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Praveenkumaarreddy/AI_MOCK_INTERVIEW.git](https://github.com/Praveenkumaarreddy/AI_MOCK_INTERVIEW.git)
   cd AI_MOCK_INTERVIEW
