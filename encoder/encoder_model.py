import torch
import torch.nn as nn


class SimpleTCNEncoder(nn.Module):
    """A tiny TCN-like encoder placeholder producing a 128-dim embedding."""

    def __init__(self, in_channels: int = 6, hidden: int = 64, emb_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_channels, hidden, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Conv1d(hidden, hidden, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),  # [B, C, 1]
        )
        self.proj = nn.Linear(hidden, emb_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, in_channels, T]
        h = self.net(x).squeeze(-1)  # [B, hidden]
        z = self.proj(h)  # [B, emb_dim]
        z = nn.functional.normalize(z, dim=-1)
        return z
