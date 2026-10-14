"""
Multi-Task Siamese Temporal Attention Network (UrbanChange-v2).

Features:
1. Shared twin ResNet-34 encoder with multi-scale feature pyramids:
   Scale 0: 64 ch, H/2
   Scale 1: 64 ch, H/4
   Scale 2: 128 ch, H/8
   Scale 3: 256 ch, H/16
   Scale 4: 512 ch, H/32
2. Difference fusion: [f1, f2, |f1 - f2|] with Channel and Spatial Attention.
3. Multi-task output heads:
   - Binary change detection head: (B, 1, H, W) logits
   - Semantic segmentation head T1: (B, C_sem, H, W) logits
   - Semantic segmentation head T2: (B, C_sem, H, W) logits
4. Semantic classes (C_sem = 7):
   0: background / unclassified
   1: building / structure
   2: tree / forest
   3: low_vegetation / grassland
   4: water
   5: road / infrastructure
   6: bare_ground / excavation
5. Semantic transition matrix mapping to service labels:
   construction, deforestation, vegetation_loss, vegetation_gain, infrastructure, excavation, water_change, other.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

SEMANTIC_CLASSES = [
    "background",
    "building",
    "tree",
    "low_vegetation",
    "water",
    "infrastructure",
    "bare_ground",
]
NUM_SEMANTIC_CLASSES = len(SEMANTIC_CLASSES)


def conv3x3(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


def conv1x1(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: Optional[nn.Module] = None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        out = self.relu(out)
        return out


class ResNet34Backbone(nn.Module):
    def __init__(self):
        super(ResNet34Backbone, self).__init__()
        self.inplanes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(64, 3)
        self.layer2 = self._make_layer(128, 4, stride=2)
        self.layer3 = self._make_layer(256, 6, stride=2)
        self.layer4 = self._make_layer(512, 3, stride=2)

    def _make_layer(self, planes: int, blocks: int, stride: int = 1) -> nn.Sequential:
        downsample = None
        if stride != 1 or self.inplanes != planes:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes, stride),
                nn.BatchNorm2d(planes),
            )
        layers = [BasicBlock(self.inplanes, planes, stride, downsample)]
        self.inplanes = planes
        for _ in range(1, blocks):
            layers.append(BasicBlock(self.inplanes, planes))
        return nn.Sequential(*layers)


class DifferenceFusionAttention(nn.Module):
    """
    Fuses bitemporal feature maps [f1, f2, |f1 - f2|] with
    Channel and Spatial Attention to suppress illumination / seasonal noise.
    """
    def __init__(self, in_channels: int, out_channels: int):
        super(DifferenceFusionAttention, self).__init__()
        # Input has 3 * in_channels: f1, f2, and |f1 - f2|
        self.fusion_conv = nn.Sequential(
            nn.Conv2d(in_channels * 3, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
        self.channel_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(out_channels, max(8, out_channels // 4), kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(max(8, out_channels // 4), out_channels, kernel_size=1),
            nn.Sigmoid(),
        )
        self.spatial_attn = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3),
            nn.Sigmoid(),
        )

    def forward(self, f1: torch.Tensor, f2: torch.Tensor) -> torch.Tensor:
        diff = torch.abs(f1 - f2)
        concat = torch.cat([f1, f2, diff], dim=1)
        fused = self.fusion_conv(concat)

        # Channel Attention
        ca = self.channel_attn(fused)
        fused = fused * ca

        # Spatial Attention
        avg_out = torch.mean(fused, dim=1, keepdim=True)
        max_out, _ = torch.max(fused, dim=1, keepdim=True)
        sa = self.spatial_attn(torch.cat([avg_out, max_out], dim=1))
        fused = fused * sa

        return fused


class DecoderBlock(nn.Module):
    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super(DecoderBlock, self).__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d((in_channels // 2) + skip_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape[2:] != skip.shape[2:]:
            x = F.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=True)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class MultiTaskSiameseChangeNet(nn.Module):
    """
    Multi-Task Siamese Temporal Attention Network.
    Outputs:
    - change_logits: (B, 1, H, W)
    - sem1_logits: (B, NUM_SEMANTIC_CLASSES, H, W)
    - sem2_logits: (B, NUM_SEMANTIC_CLASSES, H, W)
    """
    def __init__(self, num_semantic_classes: int = NUM_SEMANTIC_CLASSES):
        super(MultiTaskSiameseChangeNet, self).__init__()
        self.num_classes = num_semantic_classes

        # Shared Twin ResNet34 Backbone
        resnet = ResNet34Backbone()
        self.initial = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu)  # 64, H/2, W/2
        self.maxpool = resnet.maxpool                                       # 64, H/4, W/4
        self.layer1 = resnet.layer1                                          # 64, H/4, W/4
        self.layer2 = resnet.layer2                                          # 128, H/8, W/8
        self.layer3 = resnet.layer3                                          # 256, H/16, W/16
        self.layer4 = resnet.layer4                                          # 512, H/32, W/32

        # Difference Fusion Attention Modules
        self.fuse1 = DifferenceFusionAttention(64, 64)
        self.fuse2 = DifferenceFusionAttention(128, 128)
        self.fuse3 = DifferenceFusionAttention(256, 256)
        self.fuse4 = DifferenceFusionAttention(512, 512)

        # UNet Change Decoder
        self.dec4 = DecoderBlock(512, 256, 256)
        self.dec3 = DecoderBlock(256, 128, 128)
        self.dec2 = DecoderBlock(128, 64, 64)
        self.dec1 = DecoderBlock(64, 64, 32)

        # Final Change Head (2x up to full resolution)
        self.final_up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.change_head = nn.Sequential(
            nn.Conv2d(16, 16, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, kernel_size=1),
        )

        # Shared Semantic Segmentation Decoder & Head
        self.sem_dec = nn.Sequential(
            nn.Conv2d(512, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        self.sem_head = nn.Sequential(
            nn.Conv2d(128, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, self.num_classes, kernel_size=1),
        )

    def extract_pyramid(self, x: torch.Tensor):
        x0 = self.initial(x)
        x1 = self.layer1(self.maxpool(x0))
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        return x0, x1, x2, x3, x4

    def forward(
        self, img_a: torch.Tensor, img_b: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        h, w = img_a.shape[2:]

        # Shared twin backbone
        f_a0, f_a1, f_a2, f_a3, f_a4 = self.extract_pyramid(img_a)
        f_b0, f_b1, f_b2, f_b3, f_b4 = self.extract_pyramid(img_b)

        # Multi-scale temporal difference fusion
        diff1 = self.fuse1(f_a1, f_b1)
        diff2 = self.fuse2(f_a2, f_b2)
        diff3 = self.fuse3(f_a3, f_b3)
        diff4 = self.fuse4(f_a4, f_b4)

        # Change detection decoding
        d4 = self.dec4(diff4, diff3)
        d3 = self.dec3(d4, diff2)
        d2 = self.dec2(d3, diff1)
        d1 = self.dec1(d2, f_a0)
        up_out = self.final_up(d1)
        change_logits = self.change_head(up_out)

        # Semantic heads for T1 and T2
        sem_feat_a = F.interpolate(self.sem_dec(f_a4), size=(h, w), mode="bilinear", align_corners=False)
        sem_feat_b = F.interpolate(self.sem_dec(f_b4), size=(h, w), mode="bilinear", align_corners=False)
        sem1_logits = self.sem_head(sem_feat_a)
        sem2_logits = self.sem_head(sem_feat_b)

        return change_logits, sem1_logits, sem2_logits


def classify_semantic_transition(
    sem1_mask: np.ndarray,
    sem2_mask: np.ndarray,
    region_mask: np.ndarray,
    aspect_ratio: float = 1.0,
    compactness: float = 0.5,
    area_m2: float = 100.0,
    confidence: float = 0.8,
) -> Tuple[str, Dict[str, float]]:
    """
    Maps pixel-level semantic classes in T1 and T2 inside a detected change region
    to the service classification label.

    Classes:
    0: background
    1: building
    2: tree
    3: low_veg
    4: water
    5: road / infrastructure
    6: bare ground / excavation
    """
    if np.sum(region_mask) == 0:
        return "other", {}

    r_sem1 = sem1_mask[region_mask]
    r_sem2 = sem2_mask[region_mask]

    # Calculate class proportions
    total_px = float(len(r_sem1))
    t1_building = np.sum(r_sem1 == 1) / total_px
    t2_building = np.sum(r_sem2 == 1) / total_px
    t1_tree = np.sum(r_sem1 == 2) / total_px
    t2_tree = np.sum(r_sem2 == 2) / total_px
    t1_veg = np.sum((r_sem1 == 2) | (r_sem1 == 3)) / total_px
    t2_veg = np.sum((r_sem2 == 2) | (r_sem2 == 3)) / total_px
    t1_water = np.sum(r_sem1 == 4) / total_px
    t2_water = np.sum(r_sem2 == 4) / total_px
    t2_infra = np.sum(r_sem2 == 5) / total_px
    t2_bare = np.sum(r_sem2 == 6) / total_px

    breakdown = {
        "building_gain": float(max(0.0, t2_building - t1_building)),
        "tree_loss": float(max(0.0, t1_tree - t2_tree)),
        "veg_loss": float(max(0.0, t1_veg - t2_veg)),
        "infra_gain": float(t2_infra),
        "bare_gain": float(t2_bare),
    }

    # Classification rules:
    # 1. Building appearance: non-building -> building
    if (t2_building > 0.25 and t2_building > t1_building + 0.15) or (t2_building > 0.40):
        label = "construction"
    # 2. Forest clearing: tree -> bare/other
    elif (t1_tree > 0.30 and t2_tree < 0.15) or (t1_tree - t2_tree > 0.25):
        label = "deforestation"
    # 3. General vegetation loss:
    elif (t1_veg > 0.35 and t2_veg < 0.20) or (t1_veg - t2_veg > 0.25):
        label = "vegetation_loss"
    # 4. Elongated road/rail/linear construction:
    elif aspect_ratio > 3.0 and (t2_infra > 0.20 or area_m2 > 800.0):
        label = "infrastructure"
    # 5. Bare ground / irregular earthworks:
    elif (t2_bare > 0.35 and compactness < 0.25) or (t2_bare > 0.50):
        label = "excavation"
    # 6. Water changes:
    elif abs(t2_water - t1_water) > 0.25:
        label = "water_change"
    # 7. Fallback to geometric cues:
    elif compactness > 0.35 and confidence > 0.65:
        label = "construction"
    else:
        label = "construction" if confidence > 0.75 else "other"

    return label, breakdown
