"""
Reproducible and Resumable Training Pipeline for UrbanChange AI (v2).
Supports AMP (Mixed Precision), AdamW, Cosine Scheduling, Multi-Task Objective,
and Multi-Stage Training (High-Res pretraining, Sentinel-2 adaptation).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add ml root and project root to path
ml_root = Path(__file__).resolve().parent.parent
project_root = ml_root.parent
sys.path.insert(0, str(ml_root))
sys.path.insert(0, str(project_root))

try:
    from app.model_v2 import MultiTaskSiameseChangeNet
    from train.dataset import MultiTaskChangeDataset
    from train.losses import MultiTaskChangeLoss
except ImportError:
    from ml.app.model_v2 import MultiTaskSiameseChangeNet
    from ml.train.dataset import MultiTaskChangeDataset
    from ml.train.losses import MultiTaskChangeLoss

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ml.train")


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def calculate_binary_metrics(probs: np.ndarray, targets: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    preds = (probs >= threshold).astype(np.uint8)
    t = (targets >= 0.5).astype(np.uint8)

    tp = int(np.sum((preds == 1) & (t == 1)))
    fp = int(np.sum((preds == 1) & (t == 0)))
    fn = int(np.sum((preds == 0) & (t == 1)))
    tn = int(np.sum((preds == 0) & (t == 0)))

    precision = tp / (tp + fp + 1e-7)
    recall = tp / (tp + fn + 1e-7)
    f1 = 2.0 * precision * recall / (precision + recall + 1e-7)
    iou = tp / (tp + fp + fn + 1e-7)
    fpr = fp / (fp + tn + 1e-7)

    return {
        "precision": float(round(precision, 4)),
        "recall": float(round(recall, 4)),
        "f1": float(round(f1, 4)),
        "iou": float(round(iou, 4)),
        "fpr": float(round(fpr, 4)),
    }


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scaler: Optional[torch.cuda.amp.GradScaler],
    criterion: MultiTaskChangeLoss,
    device: torch.device,
    clip_norm: float = 1.0,
) -> Dict[str, float]:
    model.train()
    total_loss = 0.0
    total_bce = 0.0
    total_dice = 0.0
    total_sem = 0.0
    batches = 0

    use_amp = scaler is not None and device.type == "cuda"

    for t1, t2, mask, sem1, sem2 in loader:
        t1, t2 = t1.to(device), t2.to(device)
        mask = mask.to(device)
        sem1, sem2 = sem1.to(device), sem2.to(device)

        optimizer.zero_grad()

        if use_amp:
            with torch.amp.autocast("cuda"):
                change_logits, s1_logits, s2_logits = model(t1, t2)
                loss_dict = criterion(change_logits, s1_logits, s2_logits, mask, sem1, sem2)
                loss = loss_dict["total_loss"]

            scaler.scale(loss).backward()
            if clip_norm > 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip_norm)
            scaler.step(optimizer)
            scaler.update()
        else:
            change_logits, s1_logits, s2_logits = model(t1, t2)
            loss_dict = criterion(change_logits, s1_logits, s2_logits, mask, sem1, sem2)
            loss = loss_dict["total_loss"]
            loss.backward()
            if clip_norm > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip_norm)
            optimizer.step()

        total_loss += float(loss.item())
        total_bce += float(loss_dict["loss_bce"].item())
        total_dice += float(loss_dict["loss_dice"].item())
        total_sem += float(loss_dict["loss_sem"].item())
        batches += 1

    return {
        "train_loss": total_loss / max(1, batches),
        "train_bce": total_bce / max(1, batches),
        "train_dice": total_dice / max(1, batches),
        "train_sem": total_sem / max(1, batches),
    }


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: MultiTaskChangeLoss,
    device: torch.device,
    threshold: float = 0.5,
) -> Dict[str, float]:
    model.eval()
    total_loss = 0.0
    all_probs = []
    all_targets = []
    batches = 0

    with torch.no_grad():
        for t1, t2, mask, sem1, sem2 in loader:
            t1, t2 = t1.to(device), t2.to(device)
            mask = mask.to(device)
            sem1, sem2 = sem1.to(device), sem2.to(device)

            change_logits, s1_logits, s2_logits = model(t1, t2)
            loss_dict = criterion(change_logits, s1_logits, s2_logits, mask, sem1, sem2)
            total_loss += float(loss_dict["total_loss"].item())
            batches += 1

            probs = torch.sigmoid(change_logits).cpu().numpy()
            targets = mask.cpu().numpy()
            all_probs.append(probs)
            all_targets.append(targets)

    if not all_probs:
        return {"val_loss": 0.0, "f1": 0.0, "iou": 0.0, "precision": 0.0, "recall": 0.0, "fpr": 0.0}

    probs_arr = np.concatenate(all_probs, axis=0)
    targets_arr = np.concatenate(all_targets, axis=0)
    metrics = calculate_binary_metrics(probs_arr, targets_arr, threshold=threshold)
    metrics["val_loss"] = float(round(total_loss / max(1, batches), 4))
    return metrics


def run_training(
    profile: str = "hires",
    smoke_run: bool = False,
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    lr: Optional[float] = None,
    resume_path: Optional[str] = None,
) -> Dict[str, Any]:
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Starting training run: profile=%s, smoke=%s, device=%s", profile, smoke_run, device)

    # Determine paths
    out_dir = ml_root / "runs" / profile
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_log_path = out_dir / "metrics.csv"

    # Dataset paths
    data_dir = ml_root / "data" / (profile if profile in ["hires", "sentinel2"] else "hires")
    if not data_dir.exists():
        data_dir = ml_root / "data"

    total_epochs = 1 if smoke_run else (epochs or 10)
    bs = 2 if smoke_run else (batch_size or 4)
    learning_rate = lr or (0.0001 if profile == "hires" else 0.00005)

    # Instantiate datasets
    train_ds = MultiTaskChangeDataset(data_dir, patch_size=256, is_train=True, max_samples=4 if smoke_run else None)
    val_ds = MultiTaskChangeDataset(data_dir, patch_size=256, is_train=False, max_samples=2 if smoke_run else None)

    train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=bs, shuffle=False, num_workers=0)

    # Instantiate model
    model = MultiTaskSiameseChangeNet().to(device)

    # Load checkpoint if resuming or fine-tuning
    start_epoch = 1
    best_f1 = 0.0
    if resume_path and Path(resume_path).exists():
        log.info("Resuming from checkpoint: %s", resume_path)
        ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt.get("model_state_dict", ckpt), strict=False)
        if "epoch" in ckpt:
            start_epoch = ckpt["epoch"] + 1
        if "best_f1" in ckpt:
            best_f1 = ckpt["best_f1"]

    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, total_epochs), eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda") if (device.type == "cuda") else None
    criterion = MultiTaskChangeLoss(pos_weight=4.0, dice_weight=1.0, semantic_weight=0.5)

    # CSV Logging setup
    with open(csv_log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "val_loss", "f1", "iou", "precision", "recall", "fpr", "lr"])

    log.info("Beginning training loop: %d epochs scheduled...", total_epochs)
    best_metrics = {}

    for epoch in range(start_epoch, start_epoch + total_epochs):
        t0 = time.time()
        train_res = train_epoch(model, train_loader, optimizer, scaler, criterion, device)
        val_res = evaluate(model, val_loader, criterion, device, threshold=0.5)
        scheduler.step()
        elapsed = time.time() - t0

        curr_lr = optimizer.param_groups[0]["lr"]
        log.info(
            "Epoch %d/%d (%.1fs) | Train Loss: %.4f | Val Loss: %.4f | F1: %.4f | IoU: %.4f | Prec: %.4f | Rec: %.4f | LR: %.6f",
            epoch,
            start_epoch + total_epochs - 1,
            elapsed,
            train_res["train_loss"],
            val_res["val_loss"],
            val_res["f1"],
            val_res["iou"],
            val_res["precision"],
            val_res["recall"],
            curr_lr,
        )

        # Log row
        with open(csv_log_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                epoch,
                round(train_res["train_loss"], 4),
                val_res["val_loss"],
                val_res["f1"],
                val_res["iou"],
                val_res["precision"],
                val_res["recall"],
                val_res["fpr"],
                round(curr_lr, 7),
            ])

        # Save latest checkpoint
        last_ckpt = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "best_f1": best_f1,
            "val_metrics": val_res,
        }
        torch.save(last_ckpt, out_dir / "last_model.pth")

        # Save best checkpoint
        if val_res["f1"] >= best_f1 or epoch == start_epoch:
            best_f1 = val_res["f1"]
            best_metrics = val_res
            torch.save(last_ckpt, out_dir / "best_model.pth")
            log.info("Saved new best model checkpoint to %s (F1: %.4f)", out_dir / "best_model.pth", best_f1)

    log.info("Training complete for profile %s. Best F1: %.4f", profile, best_f1)
    return {
        "profile": profile,
        "epochs": total_epochs,
        "best_f1": best_f1,
        "best_metrics": best_metrics,
        "checkpoint_path": str(out_dir / "best_model.pth"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UrbanChange AI Training Script")
    parser.add_argument("--profile", choices=["hires", "sentinel2"], default="hires")
    parser.add_argument("--smoke", action="store_true", help="Run 1 epoch smoke test")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()

    run_training(
        profile=args.profile,
        smoke_run=args.smoke,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        resume_path=args.resume,
    )
