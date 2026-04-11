import torch
import torch.nn as nn
from torchvision import models


class BirdCLEFBaseline(nn.Module):
    def __init__(self, num_classes: int, pretrained: bool = True):
        super().__init__()
        # Use EfficientNet-B0 as the backbone
        self.backbone = models.efficientnet_b0(pretrained=pretrained)

        # Adjust the input layer if audio is single-channel (spectrograms)
        # EfficientNet expects 3-channel (RGB) by default
        original_conv = self.backbone.features[0][0]
        self.backbone.features[0][0] = nn.Conv2d(
            1,
            original_conv.out_channels,
            kernel_size=original_conv.kernel_size,
            stride=original_conv.stride,
            padding=original_conv.padding,
            bias=False,
        )

        # Update the classifier for bird species
        num_ftrs = self.backbone.classifier[1].in_features
        self.backbone.classifier[1] = nn.Linear(num_ftrs, num_classes)

    def forward(self, x):
        # x shape: (batch, 1, frequency, time)
        return self.backbone(x)
