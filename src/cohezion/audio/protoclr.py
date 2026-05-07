"""ProtoCLR: Prototypical Contrastive Learning for Domain Invariance.
Implements Prototypical Contrastive Learning to bridge the domain gap
between focal and passive recordings in bioacoustics.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ProtoCLR(nn.Module):
    """
    Implements Prototypical Contrastive Learning (ProtoCLR).
    Reduces complexity of SupCon by comparing examples to class prototypes.
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def compute_prototypes(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Compute mean prototypes for each class in the current batch.
        Args:
            features: [batch_size, latent_dim]
            labels: [batch_size]
        Returns:
            prototypes: [num_classes, latent_dim]
            unique_labels: [num_classes]
        """
        unique_labels = labels.unique()
        prototypes = []
        for label in unique_labels:
            mask = labels == label
            proto = features[mask].mean(dim=0)
            prototypes.append(proto)

        return torch.stack(prototypes), unique_labels

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Compute ProtoCLR loss.
        Args:
            features: [batch_size, latent_dim] normalized features.
            labels: [batch_size]
        """
        # Ensure features are normalized
        features = F.normalize(features, dim=1)

        prototypes, unique_labels = self.compute_prototypes(features, labels)
        prototypes = F.normalize(prototypes, dim=1)

        # Similarity matrix between features and prototypes
        logits = torch.matmul(features, prototypes.t()) / self.temperature

        # Target matrix (which prototype corresponds to which example)
        # Efficiently map labels to indices in unique_labels
        # unique_labels is [num_classes], labels is [batch_size]
        # targets should be [batch_size] with values in [0, num_classes-1]

        # Simple lookup: for each label, find its index in unique_labels
        targets = []
        for label in labels:
            idx = (unique_labels == label).nonzero(as_tuple=True)[0].item()
            targets.append(idx)

        targets = torch.tensor(targets, device=features.device, dtype=torch.long)

        loss = F.cross_entropy(logits, targets)
        return loss


class DomainInvarianceHarness:
    """
    Harness to apply ProtoCLR during training to align domains.
    """

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer):
        self.model = model
        self.optimizer = optimizer
        self.protoclr = ProtoCLR()

    def train_step(self, focal_batch, passive_batch):
        """
        Joint training on focal and passive data.
        Focal data provides supervised signal, ProtoCLR provides domain invariance.
        """
        self.optimizer.zero_grad()

        # Focal features
        f_feats = self.model(focal_batch["audio"])
        # Passive features (may have noisy labels or be unlabeled)
        p_feats = self.model(passive_batch["audio"])

        # Prototypical Contrastive Loss on both
        all_feats = torch.cat([f_feats, p_feats], dim=0)
        all_labels = torch.cat([focal_batch["label"], passive_batch["label"]], dim=0)

        loss_clr = self.protoclr(all_feats, all_labels)

        # Standard classification loss on focal only
        # loss_cls = F.cross_entropy(self.model.classifier(f_feats), focal_batch['label'])

        loss = loss_clr  # + loss_cls
        loss.backward()
        self.optimizer.step()

        return loss.item()
