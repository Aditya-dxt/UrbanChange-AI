"""
Comprehensive Evaluation and Model Comparison Script.
Evaluates binary change metrics, semantic transition metrics, threshold tuning,
and runs side-by-side regression against the legacy best_siamese_model.pth.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
from PIL import Image
import torch
import torch.nn as nn

ml_root = Path(__file__).resolve().parent.parent
project_root = ml_root.parent
sys.path.insert(0, str(ml_root))
sys.path.insert(0, str(project_root))

try:
    from app.model import SiameseUNetAttention
    from app.model_v2 import MultiTaskSiameseChangeNet, classify_semantic_transition
    from train.dataset import MultiTaskChangeDataset, IMAGENET_MEAN, IMAGENET_STD
except ImportError:
    from ml.app.model import SiameseUNetAttention
    from ml.app.model_v2 import MultiTaskSiameseChangeNet, classify_semantic_transition
    from ml.train.dataset import MultiTaskChangeDataset, IMAGENET_MEAN, IMAGENET_STD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ml.eval")


def compute_metrics(preds: np.ndarray, targets: np.ndarray) -> Dict[str, float]:
    p = (preds > 0).astype(np.uint8)
    t = (targets > 0).astype(np.uint8)

    tp = int(np.sum((p == 1) & (t == 1)))
    fp = int(np.sum((p == 1) & (t == 0)))
    fn = int(np.sum((p == 0) & (t == 1)))
    tn = int(np.sum((p == 0) & (t == 0)))

    prec = tp / (tp + fp + 1e-7)
    rec = tp / (tp + fn + 1e-7)
    f1 = 2.0 * prec * rec / (prec + rec + 1e-7)
    iou = tp / (tp + fp + fn + 1e-7)
    fpr = fp / (fp + tn + 1e-7)

    return {
        "precision": float(round(prec, 4)),
        "recall": float(round(rec, 4)),
        "f1": float(round(f1, 4)),
        "iou": float(round(iou, 4)),
        "fpr": float(round(fpr, 4)),
    }


def tune_threshold(
    model: nn.Module,
    pairs: List[Tuple[np.ndarray, np.ndarray, np.ndarray]],
    device: torch.device,
    thresholds: List[float] = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
) -> Tuple[float, float]:
    """Grid searches for threshold maximizing F1 score."""
    model.eval()
    best_th = 0.5
    best_f1 = 0.0

    # Collect raw probabilities
    prob_list = []
    target_list = []
    with torch.no_grad():
        for img1, img2, target in pairs:
            t1 = torch.from_numpy(((img1 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)).unsqueeze(0).to(device)
            t2 = torch.from_numpy(((img2 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)).unsqueeze(0).to(device)

            out = model(t1, t2)
            logits = out[0] if isinstance(out, tuple) else out
            prob = torch.sigmoid(logits).squeeze().cpu().numpy()
            prob_list.append(prob)
            target_list.append(target)

    all_probs = np.concatenate([p.ravel() for p in prob_list])
    all_targets = np.concatenate([t.ravel() for t in target_list])

    for th in thresholds:
        preds = (all_probs >= th).astype(np.uint8)
        tp = np.sum((preds == 1) & (all_targets > 0))
        fp = np.sum((preds == 1) & (all_targets == 0))
        fn = np.sum((preds == 0) & (all_targets > 0))
        prec = tp / (tp + fp + 1e-7)
        rec = tp / (tp + fn + 1e-7)
        f1 = 2.0 * prec * rec / (prec + rec + 1e-7)
        if f1 > best_f1:
            best_f1 = f1
            best_th = th

    return best_th, float(round(best_f1, 4))


def evaluate_sample_pairs(device: torch.device) -> Dict[str, Any]:
    """
    Evaluates both the legacy model (best_siamese_model.pth) and
    the new multi-task model on sample_data/pairs/.
    """
    sample_dir = ml_root.parent / "sample_data" / "pairs"
    legacy_weights = ml_root / "weights" / "best_siamese_model.pth"

    # Instantiate models
    legacy_model = None
    if legacy_weights.exists():
        legacy_model = SiameseUNetAttention().to(device)
        ckpt = torch.load(str(legacy_weights), map_location=device)
        legacy_model.load_state_dict(ckpt.get("model_state_dict", ckpt), strict=False)
        legacy_model.eval()

    new_model = MultiTaskSiameseChangeNet().to(device)
    new_weights = ml_root / "runs" / "hires" / "best_model.pth"
    if new_weights.exists():
        ckpt2 = torch.load(str(new_weights), map_location=device)
        new_model.load_state_dict(ckpt2.get("model_state_dict", ckpt2), strict=False)
    new_model.eval()

    results = []
    for pair_folder in sorted(sample_dir.iterdir()):
        if not pair_folder.is_dir():
            continue
        b_png = pair_folder / "before.png"
        a_png = pair_folder / "after.png"
        if not (b_png.exists() and a_png.exists()):
            continue

        im1 = np.array(Image.open(b_png).convert("RGB"), dtype=np.float32) / 255.0
        im2 = np.array(Image.open(a_png).convert("RGB"), dtype=np.float32) / 255.0
        h, w = min(im1.shape[0], im2.shape[0], 256), min(im1.shape[1], im2.shape[1], 256)
        im1, im2 = im1[:h, :w], im2[:h, :w]

        t1 = torch.from_numpy(((im1 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)).unsqueeze(0).to(device)
        t2 = torch.from_numpy(((im2 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)).unsqueeze(0).to(device)

        # Legacy inference
        legacy_change_px = 0
        legacy_conf = 0.0
        if legacy_model is not None:
            with torch.no_grad():
                l_prob = torch.sigmoid(legacy_model(t1, t2)).squeeze().cpu().numpy()
                legacy_change_px = int(np.sum(l_prob >= 0.5))
                legacy_conf = float(np.mean(l_prob[l_prob >= 0.5])) if legacy_change_px > 0 else float(1.0 - np.mean(l_prob))

        # New model inference
        with torch.no_grad():
            n_logits, s1_logits, s2_logits = new_model(t1, t2)
            n_prob = torch.sigmoid(n_logits).squeeze().cpu().numpy()
            s1_mask = torch.argmax(s1_logits, dim=1).squeeze().cpu().numpy()
            s2_mask = torch.argmax(s2_logits, dim=1).squeeze().cpu().numpy()

            new_change_px = int(np.sum(n_prob >= 0.5))
            new_conf = float(np.mean(n_prob[n_prob >= 0.5])) if new_change_px > 0 else float(1.0 - np.mean(n_prob))

            label, details = classify_semantic_transition(
                sem1_mask=s1_mask,
                sem2_mask=s2_mask,
                region_mask=(n_prob >= 0.5),
                confidence=new_conf,
            )

        results.append({
            "sample": pair_folder.name,
            "legacy_changed_pixels": legacy_change_px,
            "legacy_confidence": round(legacy_conf, 4),
            "new_changed_pixels": new_change_px,
            "new_confidence": round(new_conf, 4),
            "predicted_label": label,
        })

    return {"comparison": results}


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = evaluate_sample_pairs(device)
    print(json.dumps(out, indent=2))
