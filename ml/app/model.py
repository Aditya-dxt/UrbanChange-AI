"""
Siamese U-Net with Spatial-Temporal Attention for Satellite Change Detection.
Extracted from SatQuery (Aditya-dxt/Satquery-1.O).
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


def conv3x3(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    """3x3 convolution with padding."""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


def conv1x1(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    """1x1 convolution."""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class BasicBlock(nn.Module):
    """ResNet BasicBlock matching torchvision ResNet34."""
    expansion = 1

    def __init__(self, inplanes: int, planes: int, stride: int = 1, downsample: nn.Module = None):
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
    """ResNet34 feature extractor backbone."""
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


class SpatialTemporalAttentionModule(nn.Module):
    """
    Attention module to suppress seasonal/lighting noise and focus on structural human developments.
    Applies spatial and channel difference attention between time features.
    """
    def __init__(self, in_channels: int):
        super(SpatialTemporalAttentionModule, self).__init__()
        self.channel_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels * 2, in_channels // 2, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // 2, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        self.spatial_attn = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3),
            nn.Sigmoid()
        )

    def forward(self, feat_a: torch.Tensor, feat_b: torch.Tensor) -> torch.Tensor:
        # Absolute temporal difference
        diff = torch.abs(feat_a - feat_b)

        # Channel Attention
        concat_feat = torch.cat([feat_a, feat_b], dim=1)
        c_weight = self.channel_attn(concat_feat)
        diff_c = diff * c_weight

        # Spatial Attention
        avg_out = torch.mean(diff_c, dim=1, keepdim=True)
        max_out, _ = torch.max(diff_c, dim=1, keepdim=True)
        s_weight = self.spatial_attn(torch.cat([avg_out, max_out], dim=1))

        return diff_c * s_weight


class DecoderBlock(nn.Module):
    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super(DecoderBlock, self).__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d((in_channels // 2) + skip_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape[2:] != skip.shape[2:]:
            x = F.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=True)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class SiameseUNetAttention(nn.Module):
    """
    Temporal Siamese Convolutional Network with ResNet34 Encoder Backbone
    and Spatial-Temporal Attention Difference Modules.
    """
    def __init__(self):
        super(SiameseUNetAttention, self).__init__()

        # Shared Encoder Backbone (ResNet34)
        resnet = ResNet34Backbone()

        self.initial = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu
        )  # Output: [64, H/2, W/2]
        self.maxpool = resnet.maxpool  # Output: [64, H/4, W/4]

        self.layer1 = resnet.layer1  # [64, H/4, W/4]
        self.layer2 = resnet.layer2  # [128, H/8, W/8]
        self.layer3 = resnet.layer3  # [256, H/16, W/16]
        self.layer4 = resnet.layer4  # [512, H/32, W/32]

        # Attention Modules across scales
        self.attn1 = SpatialTemporalAttentionModule(64)
        self.attn2 = SpatialTemporalAttentionModule(128)
        self.attn3 = SpatialTemporalAttentionModule(256)
        self.attn4 = SpatialTemporalAttentionModule(512)

        # Decoder Blocks
        self.dec4 = DecoderBlock(512, 256, 256)
        self.dec3 = DecoderBlock(256, 128, 128)
        self.dec2 = DecoderBlock(128, 64, 64)
        self.dec1 = DecoderBlock(64, 64, 32)

        # Final Classification Head
        self.final_up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.final_conv = nn.Sequential(
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, kernel_size=1)  # Logits (binary change map)
        )

    def extract_features(self, x: torch.Tensor):
        x0 = self.initial(x)
        x1 = self.layer1(self.maxpool(x0))
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        return x0, x1, x2, x3, x4

    def forward(self, img_a: torch.Tensor, img_b: torch.Tensor) -> torch.Tensor:
        # Pass both images through shared encoder twin
        f_a0, f_a1, f_a2, f_a3, f_a4 = self.extract_features(img_a)
        f_b0, f_b1, f_b2, f_b3, f_b4 = self.extract_features(img_b)

        # Apply Spatial-Temporal Attention Differences
        diff1 = self.attn1(f_a1, f_b1)
        diff2 = self.attn2(f_a2, f_b2)
        diff3 = self.attn3(f_a3, f_b3)
        diff4 = self.attn4(f_a4, f_b4)

        # UNet Decoding Path
        d4 = self.dec4(diff4, diff3)
        d3 = self.dec3(d4, diff2)
        d2 = self.dec2(d3, diff1)
        d1 = self.dec1(d2, f_a0)

        out = self.final_up(d1)
        logits = self.final_conv(out)
        return logits
