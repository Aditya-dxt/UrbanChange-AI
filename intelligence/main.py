import logging
from fastapi import FastAPI

from app.models.schemas import (
    AnalyzeRequest,
    ChatRequest,
    ChatResponse,
    IntelligenceResponse,
)
from app.services.assistant_service import AssistantService
from app.services.evidence_service import EvidenceService

log = logging.getLogger(__name__)

app = FastAPI(
    title="UrbanChange AI - Intelligence Engine (Role 6)",
    description="Change Fingerprint synthesis, evidence graph generation, and grounded assistant reasoning",
    version="0.1.0",
)

assistant_svc = AssistantService()


# ── 1. Analyze Endpoint (Fingerprint, Timeline, Evidence Graph, Explanation) ────

@app.post(
    "/intelligence/analyze",
    response_model=IntelligenceResponse,
    summary="Generate Change Fingerprint, timeline, evidence graph and grounded explanation",
)
async def analyze_change(data: AnalyzeRequest) -> IntelligenceResponse:
    return EvidenceService.generate_intelligence(data)


# ── 2. Chat / Assistant Endpoint (MiniLM Retrieval + LLM / Fallback) ───────────

@app.post(
    "/intelligence/chat",
    response_model=ChatResponse,
    summary="Grounded conversational Q&A over investigation evidence graph",
)
@app.post(
    "/intelligence/assistant",
    response_model=ChatResponse,
    summary="Alias for /intelligence/chat",
)
async def run_chat(data: ChatRequest) -> ChatResponse:
    return await assistant_svc.answer_question(data)


# ── 3. Healthcheck ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "module": "intelligence"}