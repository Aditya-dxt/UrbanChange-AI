from fastapi import FastAPI
from pydantic import BaseModel

# Aapka FastAPI app initialize ho raha hai
app = FastAPI(title="UrbanChange AI - Intelligence Engine (Role 6)")

# --- 1. Analyze Endpoint Setup ---
# Ye define karta hai ki Aditya ka backend humein kya data bhejega
class AnalyzeRequest(BaseModel):
    investigation_id: str
    change_area_sqm: float
    classification: str
    overlap_percent: float

@app.post("/intelligence/analyze")
async def analyze_change(data: AnalyzeRequest):
    # TODO: Yahan par aapka Change Fingerprint aur Evidence Graph ka main code aayega
    return {
        "fingerprint_id": f"UC-{data.investigation_id}",
        "status": "requires_human_verification",
        "explanation": f"Detected {data.classification} spanning {data.change_area_sqm} sq meters."
    }

# --- 2. Assistant Endpoint Setup ---
# Ye define karta hai ki chat karte waqt kya data aayega
class ChatRequest(BaseModel):
    question: str
    evidence_ids: list[str]

@app.post("/intelligence/assistant")
async def run_assistant(data: ChatRequest):
    # TODO: Yahan par aapka Llama 3.1 / LLM ka logic connect hoga
    return {
        "answer": f"Model abhi connect nahi hai, par aapne poocha: '{data.question}'",
        "status": "requires_human_verification"
    }