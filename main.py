import os
import json
from dotenv import load_dotenv
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Load environment variables
load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY not found in .env file")

client = anthropic.Anthropic(api_key=api_key)
app = FastAPI(title="Email to JSON Extractor")

SYSTEM_PROMPT = """
You are a strict data extraction engine.
Extract key details from the provided email and return ONLY a valid JSON object.
Do not include markdown formatting (no ```json blocks), explanations, or extra text.

Use this exact schema:
{
  "sender_name": "string or null",
  "company": "string or null",
  "category": "support | sales | billing | scheduling | other",
  "urgency": "low | medium | high",
  "summary": "1-sentence summary of the email",
  "action_items": ["list of specific next steps"],
  "deadline": "YYYY-MM-DD or null"
}
"""

class EmailRequest(BaseModel):
    email_text: str

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

@app.post("/extract")
def extract_email(request: EmailRequest):
    if not request.email_text.strip():
        raise HTTPException(status_code=400, detail="Email text cannot be empty.")

    try:
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Extract data from this email:\n\n{request.email_text}"}
            ]
        )

        raw_text = response.content[0].text.strip()

        # Strip accidental markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed_json = json.loads(raw_text)
        return parsed_json

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model returned invalid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))