import torch
import numpy as np
from arc_jepa import ARCGameEncoder, ARCPredictor, ARCWorldModel


def test_encoder_output_shape():
    encoder = ARCGameEncoder(latent_dim=256)
    dummy_input = torch.randn(1, 1, 64, 64)
    output = encoder(dummy_input)
    assert output.shape == (1, 256)
    print("test_encoder_output_shape PASSED")


def test_predictor_output_shape():
    predictor = ARCPredictor(latent_dim=256)
    z = torch.randn(1, 256)
    action = torch.tensor([0])
    x = torch.tensor([32])
    y = torch.tensor([32])
    output = predictor(z, action, x, y)
    assert output.shape == (1, 256)
    print("test_predictor_output_shape PASSED")


def test_world_model_loss():
    model = ARCWorldModel(latent_dim=256)
    grid_curr = torch.randn(1, 1, 64, 64)
    grid_next = torch.randn(1, 1, 64, 64)
    action = torch.tensor([1])
    x = torch.tensor([10])
    y = torch.tensor([20])

    z_pred, loss = model(grid_curr, action, x, y, grid_next)
    assert z_pred.shape == (1, 256)
    assert loss > 0
    assert isinstance(loss.item(), float)
    print("test_world_model_loss PASSED")


def test_target_encoder_update():
    model = ARCWorldModel(latent_dim=256)
    # Change weights in encoder
    with torch.no_grad():
        for param in model.encoder.parameters():
            param.add_(1.0)

    # Update target encoder
    model._update_target_encoder(tau=1.0)

    # Check if they are equal
    for p1, p2 in zip(model.encoder.parameters(), model.target_encoder.parameters()):
        assert torch.equal(p1, p2)
    print("test_target_encoder_update PASSED")


if __name__ == "__main__":
    test_encoder_output_shape()
    test_predictor_output_shape()
    test_world_model_loss()
    test_target_encoder_update()
    print("\nAll ARC JEPA unit tests PASSED.")
