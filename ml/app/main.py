"""
FastAPI application for the ML service (SatQuery Siamese U-Net Change Detection).
Exposes /ml/detect-change, /ml/health, and /ml/model-info.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure app and scripts can be imported
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from app.predictor import ChangePredictor
from app.schemas import (
    HealthResponse,
    MLDetectChangeResponse,
    MLDetectRequest,
    ModelInfoResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ml.service")

# Global predictor instance
predictor: Optional[ChangePredictor] = None

# Environment configuration
STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "data/storage")).resolve()
WEIGHTS_PATH = Path(
    os.environ.get("ML_WEIGHTS_PATH", Path(__file__).resolve().parent.parent / "weights" / "best_siamese_model.pth")
).resolve()
DEVICE = os.environ.get("ML_DEVICE", None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    log.info("Starting ML Service...")
    log.info("Storage root: %s", STORAGE_ROOT)
    log.info("Weights path: %s", WEIGHTS_PATH)
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    try:
        predictor = ChangePredictor(weights_path=WEIGHTS_PATH, device=DEVICE)
        log.info("Model loaded successfully on %s", predictor.device)
    except Exception as exc:
        log.error("Failed to initialize model: %s", exc, exc_info=True)
        raise

    yield

    log.info("Shutting down ML Service...")


app = FastAPI(
    title="UrbanChange AI - ML Change Detection Service",
    description="Microservice running trained SatQuery Siamese U-Net Attention change detection model.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/ml/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for container probes."""
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not yet loaded.",
        )
    return HealthResponse(
        status="ok",
        model_loaded=True,
        device=str(predictor.device),
        model_version="SatQuery-Siamese-UNet-v1.0",
    )


@app.get("/ml/model-info", response_model=ModelInfoResponse, tags=["Metadata"])
async def model_info():
    """Returns detailed architecture, training metrics, and parameter counts."""
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded.",
        )
    param_count = sum(p.numel() for p in predictor.model.parameters())
    return ModelInfoResponse(
        model_version="SatQuery-Siamese-UNet-v1.0",
        architecture="SiameseUNetAttention (Shared ResNet-34 + Spatial-Temporal Attention Modules)",
        device=str(predictor.device),
        threshold=0.5,
        parameter_count=param_count,
        val_f1=0.8475,
        test_f1=0.8184,
        status="ready",
        input_resolution_trained_m=0.5,
        supported_formats=["GeoTIFF (.tif, .tiff)", "PNG (.png)", "JPEG (.jpg, .jpeg)"],
        supported_classes=[
            "construction",
            "deforestation",
            "vegetation_loss",
            "excavation",
            "infrastructure",
            "other",
        ],
    )


@app.post(
    "/ml/detect-change",
    response_model=MLDetectChangeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference"],
)
async def detect_change(request: MLDetectRequest) -> MLDetectChangeResponse:
    """
    Primary change detection endpoint.
    Processes a before/after image pair and returns segmented change regions and classification.
    """
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded.",
        )

    before_path = request.before.image_path
    after_path = request.after.image_path

    # Check if files exist
    if not Path(before_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Before image path does not exist: {before_path}",
        )
    if not Path(after_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"After image path does not exist: {after_path}",
        )

    try:
        response = predictor.detect(
            before_path=before_path,
            after_path=after_path,
            storage_root=STORAGE_ROOT,
            investigation_id=request.investigation_id,
            threshold=request.threshold or 0.5,
            min_area_m2=request.min_area_m2 or 50.0,
            pixel_size_m=request.before.pixel_size_m or request.before.resolution,
        )
        return response
    except Exception as exc:
        log.error("Inference failure for investigation_id=%s: %s", request.investigation_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(exc)}",
        )
