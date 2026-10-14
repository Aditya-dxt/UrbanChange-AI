"""
Data augmentations for bi-temporal satellite and aerial change detection.
Features:
- Geometric: Random horizontal/vertical flip, random 90-degree rotations.
- Independent Photometric Jitter per date:
  Brightness, contrast, gamma, shadow and haze simulation.
  Ensures model learns invariance to season and sun angle.
- Temporal Mis-registration Jitter:
  Subtle 1-3 pixel random shift between T1 and T2 to withstand alignment errors.
- Random Temporal Swap:
  Randomly swaps T1 and T2 to prevent temporal direction bias.
"""
from __future__ import annotations

import random
from typing import Tuple
import numpy as np


class ChangeAugmentations:
    """Robust bi-temporal data augmentations."""

    def __init__(
        self,
        p_flip: float = 0.5,
        p_rot: float = 0.5,
        p_photometric: float = 0.7,
        p_shift: float = 0.4,
        p_swap: float = 0.3,
    ):
        self.p_flip = p_flip
        self.p_rot = p_rot
        self.p_photometric = p_photometric
        self.p_shift = p_shift
        self.p_swap = p_swap

    def apply_photometric(self, img: np.ndarray) -> np.ndarray:
        """
        Applies random brightness, contrast, gamma, and haze to a float32 image in [0, 1].
        """
        out = img.copy()

        # Random brightness (0.8 - 1.2)
        if random.random() < 0.5:
            factor = random.uniform(0.8, 1.2)
            out = np.clip(out * factor, 0.0, 1.0)

        # Random contrast (0.8 - 1.25)
        if random.random() < 0.5:
            mean = np.mean(out, axis=(0, 1), keepdims=True)
            factor = random.uniform(0.8, 1.25)
            out = np.clip((out - mean) * factor + mean, 0.0, 1.0)

        # Random gamma (0.85 - 1.2)
        if random.random() < 0.4:
            gamma = random.uniform(0.85, 1.2)
            out = np.clip(out ** gamma, 0.0, 1.0)

        # Random simulated haze / cloud wash
        if random.random() < 0.2:
            haze = random.uniform(0.05, 0.15)
            out = np.clip(out * (1.0 - haze) + haze, 0.0, 1.0)

        return out.astype(np.float32)

    def apply_misregistration(
        self, img1: np.ndarray, img2: np.ndarray, max_shift: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Applies small relative shift (1-3 pixels) between img1 and img2.
        """
        dy = random.randint(-max_shift, max_shift)
        dx = random.randint(-max_shift, max_shift)
        if dy == 0 and dx == 0:
            return img1, img2

        h, w = img2.shape[:2]
        shifted = np.zeros_like(img2)

        # Source coordinates
        src_y1 = max(0, -dy)
        src_y2 = min(h, h - dy)
        src_x1 = max(0, -dx)
        src_x2 = min(w, w - dx)

        # Destination coordinates
        dst_y1 = max(0, dy)
        dst_y2 = min(h, h + dy)
        dst_x1 = max(0, dx)
        dst_x2 = min(w, w + dx)

        shifted[dst_y1:dst_y2, dst_x1:dst_x2] = img2[src_y1:src_y2, src_x1:src_x2]
        return img1, shifted

    def __call__(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        mask: np.ndarray,
        sem1: np.ndarray,
        sem2: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Args:
            img1, img2: (H, W, 3) in [0, 1]
            mask: (H, W) binary change mask [0, 1]
            sem1, sem2: (H, W) uint8 semantic masks
        """
        # 1. Random Flips
        if random.random() < self.p_flip:
            img1 = np.fliplr(img1)
            img2 = np.fliplr(img2)
            mask = np.fliplr(mask)
            sem1 = np.fliplr(sem1)
            sem2 = np.fliplr(sem2)

        if random.random() < self.p_flip:
            img1 = np.flipud(img1)
            img2 = np.flipud(img2)
            mask = np.flipud(mask)
            sem1 = np.flipud(sem1)
            sem2 = np.flipud(sem2)

        # 2. Random 90-degree Rotation
        if random.random() < self.p_rot:
            k = random.choice([1, 2, 3])
            img1 = np.rot90(img1, k)
            img2 = np.rot90(img2, k)
            mask = np.rot90(mask, k)
            sem1 = np.rot90(sem1, k)
            sem2 = np.rot90(sem2, k)

        # 3. Independent Photometric Jitter
        if random.random() < self.p_photometric:
            img1 = self.apply_photometric(img1)
        if random.random() < self.p_photometric:
            img2 = self.apply_photometric(img2)

        # 4. Small Misregistration Shift
        if random.random() < self.p_shift:
            img1, img2 = self.apply_misregistration(img1, img2, max_shift=2)

        # 5. Random Temporal Swap
        if random.random() < self.p_swap:
            img1, img2 = img2, img1
            sem1, sem2 = sem2, sem1

        return (
            np.ascontiguousarray(img1),
            np.ascontiguousarray(img2),
            np.ascontiguousarray(mask),
            np.ascontiguousarray(sem1),
            np.ascontiguousarray(sem2),
        )
