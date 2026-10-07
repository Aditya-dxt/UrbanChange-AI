# Intelligence Engine Documentation (Role 6 — Varun)

## Overview
The Intelligence Engine synthesizes multi-temporal observations, ML detection polygons, and GIS spatial intersections into structured analytical products:
1. **Change Fingerprint:** Numeric metrics characterizing change nature, velocity, and spectral shifts.
2. **Temporal Reconstruction:** Sequential timeline events and transition points.
3. **Directed Evidence Graph:** Linked graph of observational, detected, and statutory nodes.
4. **Grounded Investigation Assistant:** RAG conversational assistant powered by MiniLM embeddings and Ollama LLM (with deterministic template fallback).

---

## 1. Change Fingerprint Synthesis
The fingerprint categorizes land transformation objectively without speculative claims:
- `confidence_score` (float $0.0 - 1.0$): Aggregated ML and spectral confidence.
- `vegetation_loss_ratio` (float $0.0 - 1.0$): Fraction of transformed area previously vegetated.
- `built_up_growth_ratio` (float $0.0 - 1.0$): Fraction of transformed area showing impervious construction.
- `spectral_drift_index` (float): Magnitude of multi-band reflectance shift.
- `change_nature` (string): Categorical type (`rapid_construction`, `vegetation_clearance`, `earthwork_excavation`).
- `velocity_category` (string): Rate of progression (`rapid`, `gradual`, `intermittent`).

---

## 2. Directed Evidence Graph & Explanation
The evidence graph structures the investigation into verifiable facts:
- **Nodes:**
  - `ObservationNode`: Baseline and target satellite imagery captures.
  - `DetectionNode`: AI Siamese U-Net segmented change polygons.
  - `GISIntersectionNode`: Statutory sensitive zone overlaps.
  - `ContextNode`: WorldCover land use classes and nearby roads/waterways.
- **Edges:**
  - `corroborates`, `intersects`, `precedes`, `encompasses`.
- **Four-Part Grounded Explanation:**
  Every report strictly separates:
  1. `[Observation]`: Concrete imagery dates, resolutions, and raw sensor captures.
  2. `[Prediction]`: Model confidence scores, area measurements in $m^2$, and classifications.
  3. `[Inference]`: Spatial intersection with regulatory boundaries.
  4. `[Uncertainty & Statutory Notice]`: Limitations, cloud caveats, and mandatory notice that technical findings require human on-ground verification.

---

## 3. Investigation Assistant (RAG)
- **Vector Retrieval:**
  Evidence nodes are embedded using `sentence-transformers/all-MiniLM-L6-v2` (with token-frequency cosine fallback for environments without Torch).
- **Prompt Grounding:**
  Answers are strictly conditioned on retrieved evidence graph node IDs. The assistant explicitly cites `[evidence_node_id]` in answers.
- **Provider Interface:**
  - `OllamaProvider`: Calls local Llama 3 via Ollama on port 11434.
  - `TemplateFallbackProvider`: Deterministic template generator producing grounded answers even with zero external LLM services running.
- **Verification Flag:**
  Every response returns `status: "requires_human_verification"` and includes a statutory reminder.

---

## 4. Endpoints & API Contract

### `POST /intelligence/analyze`
Accepts observation dates, change regions, and GIS intersections, returning the complete analysis.

### `POST /intelligence/chat` (Alias: `POST /intelligence/assistant`)
**Request:**
```json
{
  "question": "Why was this polygon flagged as high risk?",
  "investigation_id": "inv_12345",
  "evidence_graph": { ... }
}
```
**Response:**
```json
{
  "answer": "The polygon was flagged due to rapid impervious surface expansion of 42,150 m² between 2023-01-15 and 2024-01-15 (node_det_001), showing a 29.4% spatial overlap with an Eco-Sensitive Buffer Zone (node_gis_001). [Statutory notice: Field verification required.]",
  "evidence_ids": ["node_det_001", "node_gis_001"],
  "status": "requires_human_verification"
}
```
