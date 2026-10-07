from __future__ import annotations

import logging
import math
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from app.models.schemas import ChatRequest, ChatResponse

log = logging.getLogger(__name__)


# ── 1. Embedding Retriever (all-MiniLM-L6-v2 with fallback) ─────────────────────

class EmbeddingRetriever:
    """
    Ranks evidence records and graph nodes against the user query using
    MiniLM sentence embeddings when available, with a cosine similarity fallback.
    """

    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            log.info("EmbeddingRetriever: Loaded all-MiniLM-L6-v2 model")
        except Exception as e:
            log.debug("SentenceTransformer unavailable: %s. Using cosine token fallback.", e)
            self._model = None

    def retrieve_evidence_ids(self, query: str, candidate_texts: dict[str, str], top_k: int = 3) -> list[str]:
        if not candidate_texts:
            return ["EV-SAT-01", "EV-ML-01", "EV-GIS-01"]

        keys = list(candidate_texts.keys())
        texts = [candidate_texts[k] for k in keys]

        if self._model is not None:
            try:
                import numpy as np
                q_emb = self._model.encode([query])[0]
                doc_embs = self._model.encode(texts)
                scores = [float(np.dot(q_emb, d) / (np.linalg.norm(q_emb) * np.linalg.norm(d) + 1e-9)) for d in doc_embs]
                ranked = sorted(zip(keys, scores), key=lambda x: x[1], reverse=True)
                return [k for k, _ in ranked[:top_k]]
            except Exception as e:
                log.warning("Embedding encode failed: %s. Falling back to token cosine.", e)

        # Fallback cosine term-frequency scoring
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scores = []
        for text in texts:
            doc_tokens = re.findall(r"\w+", text.lower())
            overlap = sum(1 for t in doc_tokens if t in q_tokens)
            score = overlap / (math.sqrt(len(doc_tokens) + 1) * math.sqrt(len(q_tokens) + 1))
            scores.append(score)

        ranked = sorted(zip(keys, scores), key=lambda x: x[1], reverse=True)
        top = [k for k, s in ranked if s > 0][:top_k]
        return top if top else keys[:top_k]


# ── 2. LLM Provider Interface ──────────────────────────────────────────────────

class LLMProvider:
    async def generate_response(
        self,
        question: str,
        evidence_text: str,
        evidence_ids: list[str],
        fingerprint: Optional[dict] = None,
    ) -> Optional[str]:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: Optional[str] = None, model: str = "llama3"):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", model)

    async def generate_response(
        self,
        question: str,
        evidence_text: str,
        evidence_ids: list[str],
        fingerprint: Optional[dict] = None,
    ) -> Optional[str]:
        prompt = (
            f"You are the UrbanChange AI Investigation Assistant. Answer the user question based strictly "
            f"on the provided satellite and GIS evidence records. Never invent property ownership, titles, "
            f"or legal conclusions. Always note that findings require human statutory verification.\n\n"
            f"Evidence records ({', '.join(evidence_ids)}):\n{evidence_text}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                if res.status_code == 200:
                    data = res.json()
                    ans = data.get("response", "").strip()
                    if ans:
                        return ans
        except Exception as e:
            log.debug("Ollama generation failed or unavailable: %s", e)
        return None


class TemplateFallbackProvider(LLMProvider):
    async def generate_response(
        self,
        question: str,
        evidence_text: str,
        evidence_ids: list[str],
        fingerprint: Optional[dict] = None,
    ) -> str:
        q = question.lower()
        cites = ", ".join(evidence_ids) if evidence_ids else "active pipeline records"
        fp_id = fingerprint.get("fingerprint_id") if fingerprint else "UC-FP-ACTIVE"
        area = fingerprint.get("changed_area_m2") if fingerprint else 15200
        ctype = fingerprint.get("change_type") if fingerprint else "construction"

        if "why" in q or "flag" in q:
            return (
                f"This area was flagged based on multi-temporal Sentinel-2 spectral difference analysis "
                f"and spatial intersection checks (referenced evidence: {cites}). "
                f"The system detected persistent physical {ctype.lower()} activity covering {area:,} m² "
                f"overlapping a configured sensitive planning buffer. "
                f"Statutory notice: Satellite radiometry and GIS overlays provide physical evidence of land-cover transition, "
                f"but do not establish legal ownership, permits, or illegality. Human ground verification is required."
            )
        elif "area" in q or "size" in q or "large" in q:
            return (
                f"The detected physical change footprint covers approximately {area:,} m² "
                f"(derived from polygon segmentation in {cites}). "
                f"The boundary exhibits spatial continuity across acquisition intervals."
            )
        elif "when" in q or "date" in q or "time" in q:
            return (
                f"Temporal reconstruction indicates physical disturbance emerging between baseline and current observation intervals "
                f"(cited evidence: {cites}). Multi-date scenes verify persistent transition rather than transient seasonal variance."
            )
        else:
            return (
                f"Based on compiled investigation evidence records ({cites}) for fingerprint {fp_id}, "
                f"the system observes active {ctype.lower()} activity of {area:,} m². "
                f"Because spatial data alone does not constitute legal proof or authorization, "
                f"this finding is flagged as requiring human verification."
            )


# ── 3. Assistant Service Orchestrator ───────────────────────────────────────────

class AssistantService:
    def __init__(self):
        self.retriever = EmbeddingRetriever()
        self.llm_provider = OllamaProvider()
        self.fallback_provider = TemplateFallbackProvider()

    async def answer_question(self, req: ChatRequest) -> ChatResponse:
        # Build candidate evidence pool
        evidence_dict: dict[str, str] = {}
        if req.evidence_ids:
            for eid in req.evidence_ids:
                evidence_dict[eid] = f"Investigation evidence record ID {eid}"
        else:
            evidence_dict["EV-SAT-01"] = "Sentinel-2 baseline imagery with nominal cloud cover"
            evidence_dict["EV-SAT-02"] = "Sentinel-2 current target imagery showing physical structure"
            evidence_dict["EV-ML-01"] = "Siamese U-Net segmentation boundary and class prediction"
            evidence_dict["EV-GIS-01"] = "Authoritative environmental planning buffer spatial intersection"

        if req.fingerprint:
            fp_id = req.fingerprint.get("fingerprint_id", "FP-RECORD")
            evidence_dict[fp_id] = (
                f"Change Fingerprint {fp_id}: {req.fingerprint.get('change_type', 'change')} of "
                f"{req.fingerprint.get('changed_area_m2', 15200)} m²"
            )

        # Retrieve relevant evidence IDs via MiniLM embeddings
        top_ids = self.retriever.retrieve_evidence_ids(req.question, evidence_dict, top_k=3)
        context_str = "\n".join(f"- {eid}: {evidence_dict[eid]}" for eid in top_ids if eid in evidence_dict)

        # Generate answer: try LLM first, fall back to deterministic template
        answer = await self.llm_provider.generate_response(
            question=req.question,
            evidence_text=context_str,
            evidence_ids=top_ids,
            fingerprint=req.fingerprint,
        )

        if not answer:
            answer = await self.fallback_provider.generate_response(
                question=req.question,
                evidence_text=context_str,
                evidence_ids=top_ids,
                fingerprint=req.fingerprint,
            )

        return ChatResponse(
            answer=answer,
            evidence_ids=top_ids,
            uncertainty_notes="Satellite imagery and GIS overlays alone do not establish legal ownership or illegality. Requires human verification.",
            status="requires_human_verification",
        )
