"""Unit tests for RSNA Robust Multi-Label Loss and AUC Surrogate."""

import torch
import pytest
from cohezion.medical.rsna_robust_loss import RobustRSNAMultilabelLoss


def test_confidence_masking_prunes_ambiguous_pseudo_labels():
    """Verify that ambiguous pseudo-labels in [1 - tau, tau] receive 0 gradient."""
    loss_fn = RobustRSNAMultilabelLoss(
        num_classes=12,
        class_thresholds=[0.80] * 12,
        alpha_gt=0.50,
        gamma_auc=0.0,  # Isolate BCE masking
    )

    # Batch of 2 samples:
    # Sample 0: clean ground truth (is_gt = 1)
    # Sample 1: ambiguous pseudo-label (is_gt = 0) with logits = 0 (prob = 0.50, inside ambiguous band [0.20, 0.80])
    logits = torch.zeros(2, 12, requires_grad=True)
    targets = torch.ones(2, 12)
    is_gt = torch.tensor([1, 0], dtype=torch.long)

    total_loss, metrics = loss_fn(logits, targets, is_gt)
    total_loss.backward()

    # Sample 0 (ground truth) MUST receive non-zero gradients
    assert torch.any(logits.grad[0] != 0.0)
    assert metrics["loss_gt"] > 0.0

    # Sample 1 (ambiguous pseudo-label) MUST receive exactly ZERO gradient due to confidence masking!
    assert torch.all(logits.grad[1] == 0.0)
    assert metrics["pseudo_retention_rate"] == 0.0


def test_confident_pseudo_labels_backpropagate():
    """Verify that confident pseudo-labels (> tau or < 1 - tau) receive gradients."""
    loss_fn = RobustRSNAMultilabelLoss(
        num_classes=12,
        class_thresholds=[0.80] * 12,
        alpha_gt=0.50,
        gamma_auc=0.0,
    )

    # Sample 0: pseudo-label (is_gt = 0) with high confidence logit = 3.0 (prob ~ 0.952 > 0.80)
    logits = torch.full((1, 12), 3.0, requires_grad=True)
    targets = torch.zeros(1, 12)  # Target is 0, so model is confidently WRONG pseudo-label
    is_gt = torch.tensor([0], dtype=torch.long)

    total_loss, metrics = loss_fn(logits, targets, is_gt)
    total_loss.backward()

    # Confident sample passes threshold, gradient must be non-zero
    assert torch.any(logits.grad[0] != 0.0)
    assert metrics["pseudo_retention_rate"] == 1.0


def test_pairwise_auc_loss_directionality():
    """Verify that pairwise AUC ranking loss is high when inverted and low when correctly ranked."""
    loss_fn = RobustRSNAMultilabelLoss(
        num_classes=1,
        gamma_auc=1.0,
        alpha_gt=0.0,
        tau_auc=1.0,
    )

    # Case 1: Perfectly ranked (positive has logit +5.0, negative has logit -5.0)
    logits_good = torch.tensor([[5.0], [-5.0]], requires_grad=True)
    targets = torch.tensor([[1.0], [0.0]])
    is_gt = torch.tensor([1, 1], dtype=torch.long)

    loss_good, m_good = loss_fn(logits_good, targets, is_gt)

    # Case 2: Inverted ranking (positive has logit -5.0, negative has logit +5.0)
    logits_bad = torch.tensor([[-5.0], [5.0]], requires_grad=True)
    loss_bad, m_bad = loss_fn(logits_bad, targets, is_gt)

    assert m_good["loss_auc"] < 0.05
    assert m_bad["loss_auc"] > 0.90
    assert loss_bad > loss_good
