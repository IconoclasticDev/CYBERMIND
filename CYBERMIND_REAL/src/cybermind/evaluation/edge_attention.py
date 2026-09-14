"""Observed-edge attention diagnostic, not an accuracy or causal metric."""
from __future__ import annotations

import math
import torch

COMMON_PORTS = (22, 53, 80, 123, 443, 3389)


class EdgeAttentionDiagnostic:
    """Pool coefficients equally over edge occurrences, heads and both layers.

    Repeated observed windows in overlapping evaluation histories count again.
    Ports are aggregate edge values: the heuristic only tests proximity to a
    common port and must not be interpreted as individual flow attribution.
    """
    def __init__(self, model, normalization, bytes_threshold=1048576, common_ports=COMMON_PORTS):
        if not math.isfinite(bytes_threshold) or bytes_threshold < 0:
            raise ValueError('bytes threshold must be finite and nonnegative')
        self.model = model
        self.normalization = normalization
        self.threshold = float(bytes_threshold)
        self.ports = tuple(common_ports)
        self.graphs = self.edges = self.selected = 0
        self.sums = [0., 0.]
        self.counts = [0, 0]
        self.status = 'ready' if model.graph.use_edge_features else 'disabled_edge_features'
        if self.status == 'ready' and not normalization:
            self.status = 'unavailable_normalization'

    @torch.no_grad()
    def observe(self, states):
        if self.status != 'ready':
            return
        c = self.normalization['edge']
        names = c['features']
        if names.count('bytes') != 1 or names.count('port') != 1:
            raise ValueError('attention diagnostic requires unambiguous bytes and port schema')
        for state in states:
            attr = state.edge_attr
            if attr.ndim != 2 or attr.shape[1] != len(names):
                raise ValueError('attention diagnostic feature schema width mismatch')
            mean = attr.new_tensor(c['mean']); std = attr.new_tensor(c['std'])
            if mean.numel() != len(names) or std.numel() != len(names) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
                raise ValueError('invalid attention normalization constants')
            raw = attr * std + mean
            if not torch.isfinite(raw).all():
                raise ValueError('non-finite raw attention features')
            port = raw[:, names.index('port')]
            common = torch.zeros_like(port, dtype=torch.bool)
            for value in self.ports:
                common |= torch.isclose(port, port.new_tensor(value), rtol=0, atol=1e-3)
            selected = (raw[:, names.index('bytes')] >= self.threshold) | ~common
            observed = state.edge_index[0] != state.edge_index[1]
            expected = state.edge_index[:, observed]
            selected = selected[observed]
            x = self.model.periodic_input(state.x) if hasattr(self.model, 'periodic_input') else state.x
            layers = self.model.graph.attention_weights(x, state.edge_index, attr)
            for layer, (indices, weights) in enumerate(layers):
                nonloop = indices[0] != indices[1]
                # Both backends retain original non-self edges in original order,
                # including duplicate pairs; do not silently remap mismatches.
                if not torch.equal(indices[:, nonloop], expected):
                    raise ValueError('attention coefficients do not align with observed edges')
                values = weights[nonloop][selected].float()
                self.sums[layer] += float(values.sum().item())
                self.counts[layer] += values.numel()
            self.graphs += 1
            self.edges += int(observed.sum().item())
            self.selected += int(selected.sum().item())

    def report(self):
        total = sum(self.counts)
        status = self.status
        if status == 'ready':
            status = 'ok' if total else 'no_matching_edges'
        return {
            'status': status,
            'scope': 'observed histories only; repeated windows count per occurrence; all self-loops excluded',
            'heuristic': {'raw_bytes_gte': self.threshold, 'or_aggregate_port_not_near': list(self.ports), 'port_absolute_tolerance': .001},
            'interpretation': 'Descriptive attention diagnostic, not accuracy, causal attribution, or a stage exit gate.',
            'backend': 'pyg' if self.model.graph.has_pyg else 'dense',
            'observed_graph_occurrences': self.graphs,
            'observed_nonself_edge_occurrences': self.edges,
            'selected_edge_occurrences': self.selected,
            'coefficient_count': total,
            'mean_attention': sum(self.sums) / total if total else None,
            'layer_mean_attention': [s / n if n else None for s, n in zip(self.sums, self.counts)],
        }
