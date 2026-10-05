from fastapi import FastAPI
from pydantic import BaseModel
import uuid
from datetime import datetime

app = FastAPI(title="UrbanChange AI - Intelligence Engine (Role 6)")

# --- 1. Analyze Endpoint (Change Fingerprint & Explanation) ---
class AnalyzeRequest(BaseModel):
    investigation_id: str
    change_area_sqm: float
    classification: str
    overlap_percent: float
    confidence_score: float = 0.94

@app.post("/intelligence/analyze")
async def analyze_change(data: AnalyzeRequest):
    current_year = datetime.now().strftime('%Y')
    unique_hash = str(uuid.uuid4())[:4].upper()
    fingerprint_id = f"UC-{current_year}-{unique_hash}"
    
    explanation = (
        f"Potential {data.classification} activity detected. "
        f"The selected region shows a persistent change covering approximately {data.change_area_sqm} m²."
    )
    
    if data.overlap_percent > 0:
        explanation += f" The change polygon intersects a configured sensitive-zone layer by approximately {data.overlap_percent}%. "
        
    explanation += " Because satellite imagery and GIS layers alone do not establish legal authorization, the event is presented as a potential sensitive-zone issue requiring human verification."

    return {
        "fingerprint_id": fingerprint_id,
        "classification": data.classification,
        "changed_area": f"{data.change_area_sqm} m²",
        "confidence": f"{data.confidence_score * 100:.1f}%",
        "sensitive_zone_overlap": f"{data.overlap_percent}%",
        "status": "requires_human_verification",
        "explanation": explanation
    }

# --- 2. Assistant Endpoint (Grounded Q&A Logic) ---
class ChatRequest(BaseModel):
    question: str
    evidence_ids: list[str]

@app.post("/intelligence/assistant")
async def run_assistant(data: ChatRequest):
    # Grounded reasoning response based on provided evidence IDs
    user_query = data.question.lower()
    
    if "why" in user_query or "flag" in user_query:
        answer = (
            f"This area was flagged based on spatial change detection and evidence records "
            f"(linked evidence IDs: {', '.join(data.evidence_ids)}). "
            "The analysis indicates a significant built-up or land-cover transition overlapping sensitive layers."
        )
    elif "area" in user_query or "size" in user_query:
        answer = f"The exact affected spatial extent is retrieved from the active evidence graph associated with IDs: {', '.join(data.evidence_ids)}."
    else:
        answer = (
            f"Based on the compiled evidence records ({', '.join(data.evidence_ids)}), "
            f"the system observes active physical changes requiring review."
        )

    return {
        "answer": answer,
        "evidence_citations": data.evidence_ids,
        "status": "requires_human_verification"
    }