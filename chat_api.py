from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv

# Load environment variables (like your OpenAI API key)
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Allow frontend requests from your GitHub Pages + backend + local dev
origins = [
    "https://h4d1ll.github.io",             # GitHub Pages (frontend)
    "https://hadillzaher-cv.onrender.com",  # Render backend
    "http://localhost:8000",                # Local testing
    "http://127.0.0.1:8000"                 # Local alt
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],   # Explicitly allow OPTIONS
    allow_headers=["*"],                        # Allow all headers
)

# Define the request schema
class Question(BaseModel):
    message: str

# Health check route (Render uses this)
@app.get("/")
def home():
    return {"status": "ok", "message": "Hadill Zaher AI backend running"}

# 🧠 Main Ask Me Anything endpoint
@app.post("/ask")
async def ask(q: Question):
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly finance assistant answering questions about investing, fintech, and economics."},
                {"role": "user", "content": q.message}
            ]
        )
        answer = completion.choices[0].message.content
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

