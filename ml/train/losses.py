"""
Loss functions for Multi-Task Change Detection.
Combines Weighted BCE, Soft Dice Loss, and Multi-Class Cross Entropy.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SoftDiceLoss(nn.Module):
    def __init__(self, smooth: float = 1.0):
        super(SoftDiceLoss, self).__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (probs_flat.sum() + targets_flat.sum() + self.smooth)
        return 1.0 - dice


class MultiTaskChangeLoss(nn.Module):
    """
    Combined objective for change detection and semantic segmentation.
    L = BCE(pos_weight) + dice_weight * Dice + semantic_weight * (CE1 + CE2)
    """

    def __init__(
        self,
        pos_weight: float = 4.0,
        dice_weight: float = 1.0,
        semantic_weight: float = 0.5,
    ):
        super(MultiTaskChangeLoss, self).__init__()
        self.dice_weight = dice_weight
        self.semantic_weight = semantic_weight

        # Weighted BCE for sparse change pixels
        self.bce = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))
        self.dice = SoftDiceLoss()
        self.ce = nn.CrossEntropyLoss(ignore_index=255)

    def forward(
        self,
        change_logits: torch.Tensor,
        sem1_logits: torch.Tensor,
        sem2_logits: torch.Tensor,
        change_targets: torch.Tensor,
        sem1_targets: torch.Tensor,
        sem2_targets: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        if self.bce.pos_weight.device != change_logits.device:
            self.bce.pos_weight = self.bce.pos_weight.to(change_logits.device)

        loss_bce = self.bce(change_logits, change_targets)
        loss_dice = self.dice(change_logits, change_targets)
        loss_change = loss_bce + self.dice_weight * loss_dice

        loss_sem1 = self.ce(sem1_logits, sem1_targets)
        loss_sem2 = self.ce(sem2_logits, sem2_targets)
        loss_sem = 0.5 * (loss_sem1 + loss_sem2)

        total_loss = loss_change + self.semantic_weight * loss_sem

        return {
            "total_loss": total_loss,
            "loss_change": loss_change,
            "loss_bce": loss_bce,
            "loss_dice": loss_dice,
            "loss_sem": loss_sem,
        }
