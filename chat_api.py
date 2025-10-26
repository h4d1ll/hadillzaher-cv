from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Allow your GitHub Pages website to access it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "ok", "message": "Hadill Zaher AI backend running"}

@app.post("/ask")
async def ask(q: Question):
    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": q.message}]
    )
    answer = completion.choices[0].message.content
    return {"answer": answer}
