# Role 6: AI Intelligence & Explainability (`/intelligence`)

This module powers the Change Fingerprinting, temporal reconstruction, and the grounded AI Investigation Assistant.

## Endpoints
* `POST /intelligence/analyze` - Generates a unique Change Fingerprint and explainable summary based on spatial detection.
* `POST /intelligence/assistant` - Provides grounded Q&A responses using linked evidence records.

## Running Locally
1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate