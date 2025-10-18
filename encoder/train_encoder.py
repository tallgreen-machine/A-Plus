#!/usr/bin/env python3
"""
Placeholder training script for the encoder. Replace with real pretraining.
Currently just saves randomly initialized weights.
"""
import torch
from encoder_model import SimpleTCNEncoder


def main():
    model = SimpleTCNEncoder(in_channels=6, hidden=64, emb_dim=128)
    torch.save(model.state_dict(), "encoder.pth")
    print("Saved encoder.pth")


if __name__ == "__main__":
    main()
