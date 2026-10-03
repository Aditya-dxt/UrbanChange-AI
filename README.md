# ■■ UrbanChange AI
### Explainable Geospatial Intelligence for Detecting, Understanding & Investigating Urban Change
<p align="center">
**UrbanChange AI** is an AI-powered geospatial intelligence platform that detects, classifies, explains, and reconstructs changes in urban and surrounding area</p>
<p align="center">
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-ML-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Sentinel-2](https://img.shields.io/badge/Sentinel--2-Satellite-1F4E79?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
</p>
---
## ■ Overview
Urban environments change continuously.
New construction appears, vegetation disappears, roads expand, land is excavated, water bodies change, and infrastructure develops over time.
However, identifying **what changed, where it changed, when it changed, and why it matters** from satellite imagery is difficult when done manually.
**UrbanChange AI** turns this process into an interactive investigation workflow.
Instead of manually downloading satellite images and comparing them, a user can:
```text
■ Select an area
 ↓
■ Select a historical date
 ↓
■ Detect
 ↓
■■ Automatically retrieve suitable satellite imagery
 ↓
■ AI detects changes
 ↓
■■ GIS analyzes spatial context
 ↓
■ Intelligence layer reconstructs the event
 ↓
■ Change Fingerprint generated
 ↓
■ Evidence + Timeline + Explanation
 ↓
■ AI Investigation Assistant
```
---
# ■ Key Capabilities
| Capability | Description |
|---|---|
| ■■ **Automatic Satellite Retrieval** | Retrieves suitable historical and current Sentinel-2 imagery for the selected area |
| ■ **AI Change Detection** | Detects pixel-level changes between before/after observations |
| ■■ **Change Classification** | Categorizes detected changes such as construction, vegetation loss, excavation and infrastructure |
| ■■ **Interactive GIS Map** | Allows users to select and investigate geographic areas interactively |
| ■ **Spatial Context Analysis** | Determines nearby features and spatial relationships |
| ■■ **Sensitive-Zone Intelligence** | Checks potential overlap with available protected/contextual geographic layers |
| ■ **Change Fingerprint** | Converts every detected event into a structured machine-readable signature |
| ■ **Temporal Reconstruction** | Reconstructs how a change developed across multiple observations |
| ■ **Evidence Graph** | Connects imagery, detections, classifications, geometry and contextual evidence |
| ■ **Explainable AI** | Explains why a region was flagged |
| ■ **AI Investigation Assistant** | Answers evidence-grounded questions about an investigation |
| ■ **Manual Image Upload** | Supports direct BEFORE/AFTER image comparison |
| ■ **Investigation Dashboard** | Presents results through maps, timelines, statistics and evidence |
| ■ **Future Multi-Sensor Support** | Architecture allows future Sentinel-1 SAR and other sensors |
---
# ■ Problem Statement
Satellite imagery contains enormous amounts of information about how cities and landscapes evolve.
UrbanChange AI — Complete README.md Source Page 2
Yet conventional workflows often require:
- Manual satellite-image discovery
- Manual downloading
- GIS expertise
- Image preprocessing
- Before/after comparison
- Manual interpretation
- Separate spatial analysis
- Manual documentation
This makes large-scale investigation slow and difficult.
### UrbanChange AI addresses this by creating a unified pipeline:
> **Satellite Data → AI Detection → GIS Reasoning → Temporal Analysis → Evidence → Investigation**
---
# ■ What Makes UrbanChange AI Different?
UrbanChange AI is not designed as simply another image-difference detector.
The platform combines **computer vision + remote sensing + GIS + temporal reasoning + explainable AI + evidence-grounded investigation**.
### Traditional workflow
```text
Satellite Image
 ↓
Manual Comparison
 ↓
"Something changed"
```
### UrbanChange AI
```mermaid
flowchart LR
 A["■■ Satellite Observations"] --> B["■ AI Change Detection"]
 B --> C["■■ Change Classification"]
 C --> D["■■ GIS Context"]
 D --> E["■ Temporal Reconstruction"]
 E --> F["■ Change Fingerprint"]
 F --> G["■ Evidence Graph"]
 G --> H["■ Investigation Assistant"]
 style A fill:#17324D,color:#fff
 style B fill:#234F70,color:#fff
 style C fill:#285943,color:#fff
 style D fill:#765A20,color:#fff
 style E fill:#624A7A,color:#fff
 style F fill:#7A3E3E,color:#fff
 style G fill:#444,color:#fff
 style H fill:#0F6B78,color:#fff
```
---
# ■ Core Features
## 1. ■■ Two-Date Satellite Comparison
The user selects:
- Geographic area
- Historical date
- Current/latest observation
The system automatically searches for suitable satellite observations.
```mermaid
sequenceDiagram
 actor User
 participant UI as ■■ Frontend
 participant API as ■■ Backend
 participant SAT as ■■ Satellite Service
 participant DATA as ■■ Copernicus Data
 User->>UI: Select area + historical date
 UI->>API: Create investigation
 API->>SAT: Search imagery
 SAT->>DATA: Query Sentinel-2
 DATA-->>SAT: Candidate observations
 SAT->>SAT: Cloud / quality filtering
 SAT-->>API: Best before/after pair
 API-->>UI: Observation metadata
```
The system does **not** require an exact satellite acquisition on the requested date.
Instead, it searches for a suitable observation within a defined temporal window.
---
# 2. ■ AI Change Detection
UrbanChange AI uses a paired-image computer vision pipeline.
### Primary architecture
**Siamese U-Net with Attention**
UrbanChange AI — Complete README.md Source Page 3
```mermaid
flowchart TB
 A["BEFORE IMAGE"] --> B["Encoder A"]
 C["AFTER IMAGE"] --> D["Encoder B"]
 B --> E["Feature Representation A"]
 D --> F["Feature Representation B"]
 E --> G["Feature Difference"]
 F --> G
 G --> H["Attention Module"]
 H --> I["Decoder"]
 B -. Skip Connections .-> I
 D -. Skip Connections .-> I
 I --> J["Change Probability Map"]
 J --> K["Threshold / Post-processing"]
 K --> L["Change Mask"]
 L --> M["Connected Regions"]
 style A fill:#234F70,color:#fff
 style C fill:#234F70,color:#fff
 style H fill:#765A20,color:#fff
 style J fill:#285943,color:#fff
 style L fill:#7A3E3E,color:#fff
```
### Model output
```json
{
 "change_detected": true,
 "confidence": 0.94,
 "changed_area_pixels": 38420,
 "change_mask_path": "outputs/masks/investigation_001.tif",
 "change_regions": [],
 "classification": {
 "label": "construction",
 "confidence": 0.91
 },
 "model_version": "siamese-unet-attention-v1"
}
```
---
# 3. ■■ Change Classification
Detected regions can be categorized into classes such as:
```text
■■ Construction
■ Vegetation Loss
■■ Excavation / Mining
■■ Infrastructure
■ Water Change
■ Other
```
---
# 4. ■■ Interactive GIS Investigation
The investigation begins from the map.
### User workflow
```mermaid
flowchart LR
 A["Open Map"] --> B["Zoom to Area"]
 B --> C["Draw Rectangle"]
 C --> D["Select Historical Date"]
 D --> E["Select Current Date"]
 E --> F["Detect"]
 style A fill:#17324D,color:#fff
 style B fill:#234F70,color:#fff
 style C fill:#285943,color:#fff
 style D fill:#765A20,color:#fff
 style E fill:#624A7A,color:#fff
 style F fill:#7A3E3E,color:#fff
```
The selected geometry becomes the investigation's **Area of Interest (AOI)**.
---
# 5. ■■ Sensitive-Zone Intelligence
UrbanChange AI can analyze detected regions against available geographic context layers.
Examples:
- ■ Forest/protected areas
- ■ Water bodies
- ■■ Infrastructure
- ■■ Roads
UrbanChange AI — Complete README.md Source Page 4
- ■■ Administrative boundaries
- ■ Other authoritative contextual datasets
### Spatial reasoning
```mermaid
flowchart LR
 A["Detected Change Region"] --> B["Geometry Validation"]
 B --> C["CRS Transformation"]
 C --> D["Spatial Intersection"]
 D --> E["Overlap Calculation"]
 E --> F["Context Result"]
 G["Protected / Forest Layer"] --> D
 H["Water Layer"] --> D
 I["Infrastructure Layer"] --> D
 J["Authoritative Land Layer"] --> D
 style A fill:#7A3E3E,color:#fff
 style D fill:#765A20,color:#fff
 style F fill:#285943,color:#fff
```
### Important
UrbanChange AI should **not** claim that satellite imagery alone proves:
- illegal construction
- ownership
- government ownership
- unauthorized activity
- legal violations
Such conclusions require authoritative records and human verification.
---
# 6. ■ Change Fingerprint
Every significant change event receives a structured **Change Fingerprint**.
Example:
```text
UC-2026-A91F
■
■■■ Type: Construction
■■■ Changed Area: 3,842 m²
■■■ Confidence: 94%
■■■ Temporal Behavior: Progressive
■■■ Sensitive Overlap: 64%
■■■ First Observed: Apr 2025
■■■ Latest Observation: Jan 2026
■■■ Model: siamese-unet-attention-v1
```
### Example JSON
```json
{
 "fingerprint_id": "UC-2026-A91F",
 "change_type": "construction",
 "changed_area_m2": 3842,
 "confidence": 0.94,
 "temporal_behavior": "progressive",
 "sensitive_overlap": {
 "percentage": 64,
 "layers": ["protected_context"]
 },
 "model_version": "siamese-unet-attention-v1"
}
```
The fingerprint makes detections:
- searchable
- comparable
- machine-readable
- reproducible
- suitable for downstream investigation
---
# 7. ■ Temporal Reconstruction
Instead of comparing only two dates, UrbanChange AI can analyze multiple historical observations.
Example:
```text
January 2025
 ↓
No significant change
April 2025
 ↓
Ground disturbance
July 2025
 ↓
Initial structure
UrbanChange AI — Complete README.md Source Page 5
October 2025
 ↓
Expansion
January 2026
 ↓
Large completed structure
```
### Timeline architecture
```mermaid
timeline
 title Example Urban Change Reconstruction
 January 2025 : No significant change
 April 2025 : Ground disturbance detected
 July 2025 : Initial structure appears
 October 2025 : Structure expands
 January 2026 : Major structure established
```
> Temporal reconstruction estimates change progression from available observations. It does not necessarily identify the exact real-world construction date.
---
# 8. ■ Evidence Graph
Every investigation should be traceable.
```mermaid
graph TD
 A["■■ Satellite Observation T1"]
 B["■■ Satellite Observation T2"]
 A --> C["■ Change Detection"]
 B --> C
 C --> D["■ Change Mask"]
 D --> E["■■ Classification"]
 E --> F["■■ Geometry"]
 F --> G["■■ Sensitive-Zone Analysis"]
 A --> H["■ Acquisition Metadata"]
 B --> H
 F --> I["■ Area / Shape Metrics"]
 C --> J["■ Model Version"]
 E --> J
 G --> K["■ Evidence Record"]
 I --> K
 H --> K
 J --> K
 K --> L["■ Change Fingerprint"]
 K --> M["■ Temporal Reconstruction"]
 K --> N["■ Investigation Assistant"]
 style A fill:#17324D,color:#fff
 style B fill:#17324D,color:#fff
 style C fill:#234F70,color:#fff
 style D fill:#7A3E3E,color:#fff
 style E fill:#285943,color:#fff
 style G fill:#765A20,color:#fff
 style K fill:#444,color:#fff
 style L fill:#624A7A,color:#fff
 style M fill:#624A7A,color:#fff
 style N fill:#0F6B78,color:#fff
```
This prevents the AI assistant from simply generating an answer without knowing where the evidence came from.
---
# 9. ■ AI Investigation Assistant
The assistant is designed to answer questions such as:
> **What changed in this area?**
> **When did the change first become persistent?**
> **How much area changed?**
> **Why was this region flagged?**
> **Does it overlap a sensitive geographic layer?**
> **What evidence supports this finding?**
> **What information is still uncertain?**
### Grounded AI pipeline
```mermaid
UrbanChange AI — Complete README.md Source Page 6
flowchart LR
 A["User Question"] --> B["Query Processing"]
 B --> C["Evidence Retrieval"]
 C --> D["Relevant Evidence"]
 D --> E["LLM"]
 E --> F["Grounded Answer"]
 F --> G["Evidence References"]
 style A fill:#17324D,color:#fff
 style C fill:#765A20,color:#fff
 style E fill:#624A7A,color:#fff
 style F fill:#285943,color:#fff
 style G fill:#444,color:#fff
```
The assistant must distinguish:
```text
Observed Fact

↓
Model Prediction

↓
Spatial Evidence

↓
Inference

↓
Uncertainty
```
It should never invent evidence.
---
# ■■ System Architecture
```mermaid
flowchart TB
 subgraph FRONTEND["■■ FRONTEND"]
 MAP["Interactive Map"]
 SELECT["AOI Selection"]
 RESULTS["Investigation Dashboard"]
 TIMELINE["Temporal Timeline"]
 CHAT["AI Assistant"]
 end
 subgraph BACKEND["■■ BACKEND"]
 API["FastAPI"]
 ORCH["Investigation Orchestrator"]
 AUTH["Authentication"]
 end
 subgraph DATA["■■ DATA LAYER"]
 COP["Copernicus / Sentinel-2"]
 CACHE["Image Cache / Object Storage"]
 end
 subgraph ML["
■ ML LAYER"]
 CD["Siamese U-Net + Attention"]
 CLS["Change Classification"]
 end
 subgraph GIS["■■ GIS LAYER"]
 GEO["GeoPandas / Shapely"]
 POSTGIS["PostGIS"]
 CONTEXT["Context Layers"]
 end
 subgraph INTEL["
■ INTELLIGENCE"]
 FP["Change Fingerprint"]
 TEMP["Temporal Reconstruction"]
 GRAPH["Evidence Graph"]
 RAG["Evidence Retrieval"]
 LLM["Investigation LLM"]
 end
 MAP --> API
 SELECT --> API
 RESULTS --> API
 CHAT --> API
 API --> ORCH
 API --> AUTH
 ORCH --> COP
 COP --> CACHE
 CACHE --> CD
 CD --> CLS
 CLS --> GEO
 GEO --> CONTEXT
 GEO --> POSTGIS
 GEO --> FP
 CLS --> FP
 FP --> TEMP
 TEMP --> GRAPH
 POSTGIS --> GRAPH
 GRAPH --> RAG
 RAG --> LLM
 LLM --> API
UrbanChange AI — Complete README.md Source Page 7
 GRAPH --> API
 FP --> API
 TEMP --> API
 style FRONTEND fill:#EAF3F8,stroke:#234F70
 style BACKEND fill:#EEF6F0,stroke:#285943
 style DATA fill:#F4F0E6,stroke:#765A20
 style ML fill:#F5ECEC,stroke:#7A3E3E
 style GIS fill:#F2EEF7,stroke:#624A7A
 style INTEL fill:#ECECEC,stroke:#444
```
---
# ■ Complete Investigation Workflow
```mermaid
flowchart TD
 START(["■ User Starts Investigation"])
 START --> AOI["■ Select Area of Interest"]
 AOI --> DATE["■ Select Historical Date"]
 DATE --> DETECT["■ Click Detect"]
 DETECT --> QUERY["■■ Query Satellite Catalog"]
 QUERY --> FILTER["■■ Quality / Cloud Filtering"]
 FILTER --> PAIR["■ Select Before / After Pair"]
 PAIR --> PRE["■ Preprocess + Align Images"]
 PRE --> MODEL["■ AI Change Detection"]
 MODEL --> MASK["■ Change Mask"]
 MASK --> CLASS["■■ Change Classification"]
 CLASS --> GIS["■■ GIS Spatial Analysis"]
 GIS --> SENSITIVE["■■ Sensitive Context Analysis"]
 SENSITIVE --> FINGERPRINT["■ Change Fingerprint"]
 FINGERPRINT --> TEMP["■ Temporal Reconstruction"]
 TEMP --> EVIDENCE["■ Evidence Graph"]
 EVIDENCE --> EXPLAIN["■ Explanation"]
 EXPLAIN --> DASH["■ Investigation Dashboard"]
 DASH --> CHAT["■ AI Investigation Assistant"]
 CHAT --> END(["■ Evidence-Grounded Investigation"])
 style START fill:#17324D,color:#fff
 style DETECT fill:#7A3E3E,color:#fff
 style MODEL fill:#234F70,color:#fff
 style GIS fill:#765A20,color:#fff
 style FINGERPRINT fill:#624A7A,color:#fff
 style EVIDENCE fill:#444,color:#fff
 style END fill:#285943,color:#fff
```
---
# ■■■ Team Architecture
UrbanChange AI is divided into six independent ownership areas.
| # | Role | Primary Ownership |
|---|---|---|
| 01 | ■ ML / Computer Vision | Change detection + classification |
| 02 | ■■ Satellite / Data | Sentinel-2 retrieval + preprocessing |
| 03 | ■■ GIS | Spatial analysis + sensitive context |
| 04 | ■■ Backend | APIs + orchestration + database |
| 05 | ■■ Frontend | Map + dashboard + user experience |
| 06 | ■ AI Intelligence | Fingerprint + temporal + evidence + assistant |
### GPU constraint
Only **Person 1** requires the RTX/GPU machine for model training.
Everyone else should use:
```text
Mock APIs
 +
Sample GeoTIFFs
 +
JSON Fixtures
 +
CPU Development
```
This prevents the GPU laptop from becoming a project-wide bottleneck.
---
UrbanChange AI — Complete README.md Source Page 8
# ■ Repository Structure
```text
UrbanChange-AI/
■
■■■ frontend/
■■■ backend/
■■■ ml/
■■■ satellite/
■■■ gis/
■■■ intelligence/
■■■ shared/
■■■ data/
■■■ docs/
■■■ tests/
■
■■■ .env.example
■■■ docker-compose.yml
■■■ README.md
■■■ LICENSE
```
---
# ■ Module Contracts
The most important engineering principle is:
> **Modules communicate through contracts, not implementation details.**
## ■■ Satellite → ML
```json
{
 "before": {
 "path": "storage/before.tif",
 "date": "2025-04-14",
 "sensor": "Sentinel-2",
 "crs": "EPSG:32644",
 "resolution": 10
 },
 "after": {
 "path": "storage/after.tif",
 "date": "2026-01-18",
 "sensor": "Sentinel-2",
 "crs": "EPSG:32644",
 "resolution": 10
 }
}
```
## ■ ML → Backend
```json
{
 "change_detected": true,
 "confidence": 0.94,
 "changed_area_pixels": 38420,
 "change_mask_path": "masks/001.tif",
 "change_regions": [],
 "classification": {
 "label": "construction",
 "confidence": 0.91
 },
 "model_version": "siamese-unet-attention-v1"
}
```
## ■■ GIS → Backend
```json
{
 "changed_area_m2": 3842,
 "sensitive_intersections": [],
 "nearby_features": [],
 "geojson": {}
}
```
## ■ Intelligence → Backend
```json
{
 "fingerprint": {},
 "temporal_reconstruction": {},
 "evidence_graph": {},
 "explanation": {},
 "assistant_context": {}
}
```
---
# ■■ Database Model
```mermaid
erDiagram
 INVESTIGATION ||--o{ SATELLITE_OBSERVATION : contains
 INVESTIGATION ||--o{ DETECTION : produces
UrbanChange AI — Complete README.md Source Page 9
 INVESTIGATION ||--o{ CLASSIFICATION : contains
 INVESTIGATION ||--o{ SENSITIVE_INTERSECTION : contains
 INVESTIGATION ||--o{ CHANGE_FINGERPRINT : generates
 INVESTIGATION ||--o{ TEMPORAL_EVENT : contains
 INVESTIGATION ||--o{ EVIDENCE : contains
 INVESTIGATION ||--o{ ASSISTANT_MESSAGE : has
 DETECTION ||--o{ CLASSIFICATION : receives
 DETECTION ||--o{ EVIDENCE : supports
 CHANGE_FINGERPRINT ||--o{ EVIDENCE : references
 TEMPORAL_EVENT ||--o{ EVIDENCE : references
 INVESTIGATION {
 uuid id PK
 geometry aoi
 date historical_date
 date current_date
 string status
 timestamp created_at
 }
 SATELLITE_OBSERVATION {
 uuid id PK
 uuid investigation_id FK
 date acquisition_date
 string sensor
 string image_path
 float cloud_cover
 string crs
 }
 DETECTION {
 uuid id PK
 uuid investigation_id FK
 float confidence
 float changed_area
 string mask_path
 string model_version
 }
 CLASSIFICATION {
 uuid id PK
 uuid detection_id FK
 string label
 float confidence
 }
 CHANGE_FINGERPRINT {
 uuid id PK
 uuid investigation_id FK
 string fingerprint_id
 string change_type
 float confidence
 float changed_area
 }
 TEMPORAL_EVENT {
 uuid id PK
 uuid investigation_id FK
 date observation_date
 string event_type
 float confidence
 }
 EVIDENCE {
 uuid id PK
 uuid investigation_id FK
 string evidence_type
 string source_reference
 json metadata
 }
 ASSISTANT_MESSAGE {
 uuid id PK
 uuid investigation_id FK
 string role
 text content
 json evidence_ids
 timestamp created_at
 }
```
---
#
■ Technology Stack
## Frontend
- React
- Vite
- Tailwind CSS
- Leaflet / MapLibre
- Recharts / Plotly
## Backend
- Python
- FastAPI
- Pydantic
- PostgreSQL
UrbanChange AI — Complete README.md Source Page 10
- PostGIS
- Celery / RQ
## Geospatial
- Rasterio
- GeoPandas
- Shapely
- PostGIS
- GeoJSON
## AI / ML
- PyTorch
- Siamese U-Net + Attention
- CLIP / semantic classifier
- Llama 3.1 8B Instruct
- all-MiniLM-L6-v2
## Satellite Data
### MVP
**Sentinel-2 optical imagery**
### Future
```text
Sentinel-1 SAR

↓
Multi-sensor fusion

↓
Higher-resolution imagery

↓
Additional remote-sensing sources
```
---
#
■ ML Evaluation
The model should be evaluated using:
```text
Precision
Recall
F1 Score
IoU
Dice Score
```
Region-level evaluation:
```text
False Positives
False Negatives
Small-object detection
Boundary accuracy
Region consistency
```
Classification:
```text
Accuracy
Precision
Recall
F1
Confusion Matrix
```
---
#
■ Testing Strategy
```mermaid
flowchart TB
 A["Unit Tests"] --> B["Module Tests"]
 B --> C["API Tests"]
 C --> D["Integration Tests"]
 D --> E["End-to-End Tests"]
 E --> F["Demo Validation"]
 A1["ML preprocessing"] --> A
 A2["GIS geometry"] --> A
 A3["Fingerprint generation"] --> A
 B1["Satellite pipeline"] --> B
 B2["ML inference"] --> B
 B3["Evidence engine"] --> B
 C1["FastAPI endpoints"] --> C
 D1["Satellite
→ ML"] --> D
 D2["ML
→ GIS"] --> D
 D3["GIS
→ Intelligence"] --> D
 F --> G["Production Candidate"]
UrbanChange AI — Complete README.md Source Page 11
 style A fill:#17324D,color:#fff
 style B fill:#234F70,color:#fff
 style C fill:#285943,color:#fff
 style D fill:#765A20,color:#fff
 style E fill:#624A7A,color:#fff
 style F fill:#7A3E3E,color:#fff
 style G fill:#285943,color:#fff
```
---
# ■■ Local Development
## Clone
```bash
git clone https://github.com/<your-username>/UrbanChange-AI.git
cd UrbanChange-AI
```
## Backend
```bash
cd backend
python -m venv .venv
```
### Windows
```bash
.venv\Scripts\activate
```
### Linux / WSL
```bash
source .venv/bin/activate
```
Install:
```bash
pip install -r requirements.txt
```
Run:
```bash
uvicorn app.main:app --reload
```
Backend:
```text
http://localhost:8000
```
Swagger:
```text
http://localhost:8000/docs
```
---
# ■■ Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend:
```text
http://localhost:5173
```
---
# ■■ PostgreSQL + PostGIS
Example:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/urbanchange
```
Enable PostGIS:
```sql
CREATE EXTENSION postgis;
```
---
# ■ Environment Variables
Create:
UrbanChange AI — Complete README.md Source Page 12
```text
.env
```
Example:
```env
APP_ENV=development
SECRET_KEY=change-me
DATABASE_URL=postgresql://postgres:password@localhost:5432/urbanchange
COPERNICUS_CLIENT_ID=
COPERNICUS_CLIENT_SECRET=
LLM_API_KEY=
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=
```
Never commit:
```text
.env
*.key
*.pem
credentials.json
API keys
model secrets
```
---
# ■ Docker
Build:
```bash
docker compose build
```
Run:
```bash
docker compose up
```
Stop:
```bash
docker compose down
```
---
# ■ Development Strategy
The six modules should be developed in parallel.
```mermaid
gantt
 title UrbanChange AI Development Plan
 dateFormat YYYY-MM-DD
 section ML
 Dataset + baseline :ml1, 2026-01-01, 10d
 Model training :ml2, after ml1, 15d
 Evaluation + inference :ml3, after ml2, 10d
 section Satellite
 Catalog integration :sat1, 2026-01-01, 10d
 Preprocessing :sat2, after sat1, 12d
 Production pipeline :sat3, after sat2, 10d
 section GIS
 Map geometry contract :gis1, 2026-01-01, 7d
 Spatial analysis :gis2, after gis1, 15d
 Context layers :gis3, after gis2, 10d
 section Backend
 API + DB design :be1, 2026-01-01, 8d
 Orchestration :be2, after be1, 15d
 Integration :be3, after be2, 12d
 section Frontend
 UI + map :fe1, 2026-01-01, 12d
 Results dashboard :fe2, after fe1, 12d
 Final integration :fe3, after fe2, 12d
 section Intelligence
 Fingerprint :ai1, 2026-01-01, 8d
 Temporal + evidence graph :ai2, after ai1, 15d
 Assistant :ai3, after ai2, 12d
```
---
# ■ Git Workflow
UrbanChange AI — Complete README.md Source Page 13
Recommended branch structure:
```text
main
■
■■■ develop
■
■■■ feature/ml-change-detection
■■■ feature/satellite-service
■■■ feature/gis-engine
■■■ feature/backend-orchestration
■■■ feature/frontend-dashboard
■■■ feature/intelligence-engine
```
### Commit convention
```text
feat: add satellite catalog search
feat: implement change fingerprint
fix: correct CRS transformation
fix: handle missing satellite observation
refactor: separate GIS service
docs: update API contract
test: add temporal reconstruction tests
```
---
# ■ Pull Request Checklist
Before opening a PR:
```text
[ ] Code runs locally
[ ] Tests pass
[ ] README/docs updated
[ ] API contract unchanged or documented
[ ] Environment variables documented
[ ] No secrets committed
[ ] No large satellite files committed
[ ] Error handling added
[ ] Mock mode still works
[ ] Integration impact checked
```
---
# ■■ Responsible Use
UrbanChange AI is an **analysis and decision-support system**, not an autonomous legal authority.
The platform can identify:
- observed image differences
- model-predicted change
- geographic overlap
- temporal patterns
- contextual relationships
- evidence-supported hypotheses
It should **not independently declare**:
- legal violations
- land ownership
- unauthorized construction
- criminal activity
- government ownership
- exact construction dates
Those conclusions require authoritative records and appropriate human verification.
---
# ■ Security Considerations
The production deployment should include:
- Authentication
- Authorization
- API rate limiting
- Input validation
- File-type validation
- File-size limits
- Malware scanning for uploads
- Secure object storage
- Signed URLs
- Secret management
- Database access controls
- Audit logs
- Request IDs
- Model/version tracking
---
# ■ Future Roadmap
```mermaid
flowchart LR
 A["MVP"] --> B["Advanced Intelligence"]
UrbanChange AI — Complete README.md Source Page 14
 B --> C["Multi-Sensor"]
 C --> D["Predictive Monitoring"]
 A --> A1["Sentinel-2"]
 A --> A2["Change Detection"]
 A --> A3["GIS Context"]
 A --> A4["Fingerprint"]
 B --> B1["Evidence Graph"]
 B --> B2["Temporal Reconstruction"]
 B --> B3["Investigation Assistant"]
 C --> C1["Sentinel-1 SAR"]
 C --> C2["Sensor Fusion"]
 C --> C3["High Resolution Imagery"]
 D --> D1["Continuous Monitoring"]
 D --> D2["Anomaly Alerts"]
 D --> D3["Change Forecasting"]
 style A fill:#285943,color:#fff
 style B fill:#234F70,color:#fff
 style C fill:#765A20,color:#fff
 style D fill:#624A7A,color:#fff
```
### Planned enhancements
- ■ Sentinel-1 SAR integration
- ■■ Multi-sensor fusion
- ■■ Higher-resolution imagery
- ■ Automated area monitoring
- ■ Change alerts
- ■ Active learning
- ■ Confidence calibration
- ■ "Why not?" analysis
- ■ Construction progress estimation
- ■ Advanced spatial analytics
- ■ Automated investigation reports
- ■ Large-scale city monitoring
---
# ■ Datasets & Resources
Potential datasets for model development and evaluation:
- **LEVIR-CD** — building change detection
- **OSCD** — Sentinel-2 change detection
- **SpaceNet** — geospatial datasets
- **ESA WorldCover** — land-cover context
- **Dynamic World** — land-cover context
The production satellite source for the MVP is intended to be:
**Copernicus Sentinel-2**
---
# ■ Important Engineering Notes
### Satellite imagery
The model must be trained/evaluated with imagery compatible with the actual production sensor, preprocessing and spatial resolution.
A model trained on one dataset should **not automatically be assumed to be production-ready for Sentinel-2**.
### Coordinates
Use:
```text
GeoJSON:
[longitude, latitude]
```
Do not use:
```text
[latitude, longitude]
```
### Area calculations
Do not calculate area directly in geographic latitude/longitude degrees.
Transform to a suitable projected CRS first.
### AI outputs
Always distinguish:
```text
Observation
Prediction
Inference
Uncertainty
```
### Evidence
Every important generated statement should be traceable to an evidence record.
UrbanChange AI — Complete README.md Source Page 15
---
# ■ Contribution
Contributions should follow the module ownership structure.
1. Create a feature branch.
2. Implement the feature.
3. Add tests.
4. Update documentation.
5. Verify integration contracts.
6. Open a pull request.
Example:
```bash
git checkout -b feature/change-fingerprint
git add .
git commit -m "feat: add change fingerprint generation"
git push origin feature/change-fingerprint
```
---
# ■■■ Team Ownership
| Person | Responsibility | Main Directory |
|---|---|---|
| Person 1 | ML / Computer Vision | `/ml` |
| Person 2 | Satellite / Data | `/satellite` |
| Person 3 | GIS / Geospatial | `/gis` |
| Person 4 | Backend / Integration | `/backend` |
| Person 5 | Frontend | `/frontend` |
| Person 6 | AI Intelligence | `/intelligence` |
---
# ■ Definition of Done
UrbanChange AI is considered integration-ready when a user can:
```text
1. Open the interactive map
 ↓
2. Select an Area of Interest
 ↓
3. Select a historical date
 ↓
4. Click Detect
 ↓
5. Automatically retrieve suitable satellite imagery
 ↓
6. Compare historical vs current observations
 ↓
7. Detect changes using AI
 ↓
8. Classify detected changes
 ↓
9. Calculate geographic context
 ↓
10. Analyze sensitive-zone overlap
 ↓
11. Generate a Change Fingerprint
 ↓
12. Reconstruct temporal progression
 ↓
13. Inspect the Evidence Graph
 ↓
14. Understand why the system flagged the region
 ↓
15. Ask the Investigation Assistant questions
 ↓
16. Receive evidence-grounded answers
```
---
# ■ Final Principle
> **UrbanChange AI does not simply detect that pixels changed.**
>
> **It turns satellite observations into explainable, spatially contextualized, temporally reconstructed and evidence-grounded investigations.**
---
## ■ Project Documentation
For detailed implementation information, maintain:
```text
/docs
■■■ architecture/
■■■ api/
■■■ datasets/
■■■ models/
■■■ deployment/
■■■ development/
```
UrbanChange AI — Complete README.md Source Page 16
Recommended documents:
- `SYSTEM_ARCHITECTURE.md`
- `API_CONTRACTS.md`
- `ML_PIPELINE.md`
- `SATELLITE_PIPELINE.md`
- `GIS_ENGINE.md`
- `INTELLIGENCE_ENGINE.md`
- `DATABASE_SCHEMA.md`
- `DEPLOYMENT.md`
- `CONTRIBUTING.md`
---
<p align="center">
### ■■ UrbanChange AI
**Observe • Detect • Understand • Explain • Investigate**
</p>
