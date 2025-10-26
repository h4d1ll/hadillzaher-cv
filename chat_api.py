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

# ✅ Allow frontend requests from your GitHub Pages + backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://h4d1ll.github.io",            # your GitHub Pages site
        "https://hadillzaher-cv.onrender.com", # your Render backend
        "http://localhost:8000"                # local dev (optional)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request schema
class Question(BaseModel):
    message: str

# Test endpoint (for Render health check)
@app.get("/")
def home():
    return {"status": "ok", "message": "Hadill Zaher AI backend running"}

# Main Ask Me Anything route
@app.post("/ask")
async def ask(q: Question):
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": q.message}]
        )
        answer = completion.choices[0].message.content
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}
