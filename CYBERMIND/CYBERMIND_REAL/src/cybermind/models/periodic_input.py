"""Fixed, optional periodic input representation; never changes stored graphs."""
import math
import torch
from torch import nn


class PeriodicClockInput(nn.Module):
    def __init__(self, node_dim, specification):
        super().__init__()
        if not isinstance(specification, dict) or set(specification) != {'column', 'slope', 'intercept', 'period'}:
            raise ValueError('periodic_clock requires column, slope, intercept and period.')
        column = specification['column']
        if isinstance(column, bool) or not isinstance(column, int) or not 0 <= column < node_dim:
            raise ValueError('Periodic clock column is outside the original node features.')
        values = [specification[k] for k in ('slope', 'intercept', 'period')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError('Periodic clock constants must be finite numbers.')
        if values[0] <= 0 or values[2] <= 0:
            raise ValueError('Periodic clock slope and period must be positive.')
        self.column = column
        self.register_buffer('constants', torch.tensor(values, dtype=torch.float64))

    def forward(self, x):
        slope, intercept, period = self.constants.unbind()
        angle = (x[:, self.column].double() - intercept) / slope * (2 * math.pi / period)
        derived = torch.stack((angle.sin(), angle.cos()), dim=-1).to(x.dtype)
        return torch.cat((x, derived), dim=-1)
