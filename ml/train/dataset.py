"""
Dataset loader with balanced patch sampling for change detection.
Supports both 'hires' and 'sentinel2' data catalogs.
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset

try:
    from train.augmentations import ChangeAugmentations
except ImportError:
    from ml.train.augmentations import ChangeAugmentations

log = logging.getLogger("ml.dataset")

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


class MultiTaskChangeDataset(Dataset):
    """
    Dataset that loads bitemporal image pairs, change masks, and semantic masks.
    Implements balanced patch sampling (oversamples change regions, keeps 15-20% quiet pairs).
    """

    def __init__(
        self,
        root_dir: str | Path,
        patch_size: int = 256,
        is_train: bool = True,
        change_sample_prob: float = 0.85,
        max_samples: Optional[int] = None,
    ):
        self.root_dir = Path(root_dir)
        self.patch_size = patch_size
        self.is_train = is_train
        self.change_sample_prob = change_sample_prob
        self.augmentor = ChangeAugmentations() if is_train else None

        self.samples = self._discover_pairs()
        if max_samples and max_samples < len(self.samples):
            self.samples = self.samples[:max_samples]

        log.info(
            "Initialized MultiTaskChangeDataset (%s): %d image pairs found in %s",
            "train" if is_train else "val/test",
            len(self.samples),
            self.root_dir,
        )

    def _discover_pairs(self) -> List[dict]:
        pairs = []

        # 1. Check LEVIR-CD structure (A/, B/, label/)
        a_dir = self.root_dir / "A"
        b_dir = self.root_dir / "B"
        l_dir = self.root_dir / "label"
        if a_dir.exists() and b_dir.exists():
            for a_file in sorted(a_dir.glob("*.png")):
                b_file = b_dir / a_file.name
                l_file = l_dir / a_file.name if l_dir.exists() else None
                if b_file.exists():
                    pairs.append({
                        "b_path": str(a_file),
                        "a_path": str(b_file),
                        "m_path": str(l_file) if (l_file and l_file.exists()) else None,
                        "s1_path": None,
                        "s2_path": None,
                    })

        # 2. Check SECOND structure (im1/, im2/, label1/, label2/)
        im1_dir = self.root_dir / "im1"
        im2_dir = self.root_dir / "im2"
        l1_dir = self.root_dir / "label1"
        l2_dir = self.root_dir / "label2"
        if im1_dir.exists() and im2_dir.exists():
            for f1 in sorted(im1_dir.glob("*.png")):
                f2 = im2_dir / f1.name
                s1 = l1_dir / f1.name if l1_dir.exists() else None
                s2 = l2_dir / f1.name if l2_dir.exists() else None
                if f2.exists():
                    pairs.append({
                        "b_path": str(f1),
                        "a_path": str(f2),
                        "m_path": None,
                        "s1_path": str(s1) if (s1 and s1.exists()) else None,
                        "s2_path": str(s2) if (s2 and s2.exists()) else None,
                    })

        # 3. Check Sentinel-2 structure (images_before/, images_after/, masks/)
        s2_b = self.root_dir / "images_before"
        s2_a = self.root_dir / "images_after"
        s2_m = self.root_dir / "masks"
        if s2_b.exists() and s2_a.exists():
            for f_b in sorted(s2_b.glob("*.png")):
                f_a = s2_a / f_b.name
                f_m = s2_m / f_b.name if s2_m.exists() else None
                if f_a.exists():
                    pairs.append({
                        "b_path": str(f_b),
                        "a_path": str(f_a),
                        "m_path": str(f_m) if (f_m and f_m.exists()) else None,
                        "s1_path": None,
                        "s2_path": None,
                    })

        # 4. Check subdirectories recursively
        if not pairs:
            for sub in self.root_dir.iterdir():
                if sub.is_dir():
                    sub_ds = MultiTaskChangeDataset(sub, patch_size=self.patch_size, is_train=self.is_train)
                    pairs.extend(sub_ds.samples)

        return pairs

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        item = self.samples[idx]

        # Load raw images
        img1 = np.array(Image.open(item["b_path"]).convert("RGB"), dtype=np.float32) / 255.0
        img2 = np.array(Image.open(item["a_path"]).convert("RGB"), dtype=np.float32) / 255.0

        h, w = img1.shape[:2]

        # Load or generate masks
        if item["m_path"]:
            mask_arr = np.array(Image.open(item["m_path"]).convert("L"), dtype=np.float32)
            mask = (mask_arr > 127).astype(np.float32)
        else:
            diff = np.mean(np.abs(img1 - img2), axis=-1)
            mask = (diff > 0.15).astype(np.float32)

        # Load or synthesize semantic maps
        if item["s1_path"] and item["s2_path"]:
            sem1 = np.array(Image.open(item["s1_path"]), dtype=np.uint8)
            sem2 = np.array(Image.open(item["s2_path"]), dtype=np.uint8)
        else:
            sem1 = np.zeros((h, w), dtype=np.uint8)
            sem2 = np.zeros((h, w), dtype=np.uint8)
            # Default mapping from mask
            sem2[mask > 0] = 1  # default to building/construction

        # Crop patch (256x256)
        if h > self.patch_size or w > self.patch_size:
            # Balanced sampling: try to crop around change if requested
            if self.is_train and np.random.random() < self.change_sample_prob and np.any(mask > 0):
                change_ys, change_xs = np.where(mask > 0)
                center_idx = np.random.randint(0, len(change_ys))
                cy, cx = change_ys[center_idx], change_xs[center_idx]
                y1 = max(0, min(h - self.patch_size, cy - self.patch_size // 2))
                x1 = max(0, min(w - self.patch_size, cx - self.patch_size // 2))
            else:
                y1 = np.random.randint(0, max(1, h - self.patch_size + 1)) if self.is_train else 0
                x1 = np.random.randint(0, max(1, w - self.patch_size + 1)) if self.is_train else 0

            img1 = img1[y1 : y1 + self.patch_size, x1 : x1 + self.patch_size]
            img2 = img2[y1 : y1 + self.patch_size, x1 : x1 + self.patch_size]
            mask = mask[y1 : y1 + self.patch_size, x1 : x1 + self.patch_size]
            sem1 = sem1[y1 : y1 + self.patch_size, x1 : x1 + self.patch_size]
            sem2 = sem2[y1 : y1 + self.patch_size, x1 : x1 + self.patch_size]

        # Pad if smaller than patch_size
        ph, pw = img1.shape[:2]
        if ph < self.patch_size or pw < self.patch_size:
            p_img1 = np.zeros((self.patch_size, self.patch_size, 3), dtype=np.float32)
            p_img2 = np.zeros((self.patch_size, self.patch_size, 3), dtype=np.float32)
            p_mask = np.zeros((self.patch_size, self.patch_size), dtype=np.float32)
            p_sem1 = np.zeros((self.patch_size, self.patch_size), dtype=np.uint8)
            p_sem2 = np.zeros((self.patch_size, self.patch_size), dtype=np.uint8)

            p_img1[:ph, :pw] = img1
            p_img2[:ph, :pw] = img2
            p_mask[:ph, :pw] = mask
            p_sem1[:ph, :pw] = sem1
            p_sem2[:ph, :pw] = sem2

            img1, img2, mask, sem1, sem2 = p_img1, p_img2, p_mask, p_sem1, p_sem2

        # Augmentation
        if self.augmentor:
            img1, img2, mask, sem1, sem2 = self.augmentor(img1, img2, mask, sem1, sem2)

        # Normalize
        norm1 = (img1 - IMAGENET_MEAN) / IMAGENET_STD
        norm2 = (img2 - IMAGENET_MEAN) / IMAGENET_STD

        # Convert to tensors
        t1 = torch.from_numpy(norm1.transpose(2, 0, 1).astype(np.float32))
        t2 = torch.from_numpy(norm2.transpose(2, 0, 1).astype(np.float32))
        t_mask = torch.from_numpy(mask).unsqueeze(0).float()
        t_sem1 = torch.from_numpy(sem1.astype(np.int64))
        t_sem2 = torch.from_numpy(sem2.astype(np.int64))

        return t1, t2, t_mask, t_sem1, t_sem2
