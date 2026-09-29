from __future__ import annotations
import torch
from torch import nn

try:
    from torch_geometric.nn import GATv2Conv
    HAS_PYG = True
    PYG_IMPORT_ERROR = None
except Exception as error:
    GATv2Conv = None
    HAS_PYG = False
    PYG_IMPORT_ERROR = repr(error)


def _validate_edge_configuration(edge_attr_dim, use_edge_features):
    if use_edge_features and (
        isinstance(edge_attr_dim, bool)
        or not isinstance(edge_attr_dim, int)
        or edge_attr_dim <= 0
    ):
        raise ValueError("edge_attr_dim must be a positive integer when use_edge_features=True")


def _validate_edge_attr(x, edge_index, edge_attr, edge_attr_dim):
    if edge_attr is None:
        return
    if not isinstance(edge_attr, torch.Tensor):
        raise TypeError("edge_attr must be a torch.Tensor or None")
    expected_shape = (edge_index.size(1), edge_attr_dim)
    if edge_attr.ndim != 2 or tuple(edge_attr.shape) != expected_shape:
        raise ValueError(f"edge_attr must have shape {expected_shape}, got {tuple(edge_attr.shape)}")
    if not edge_attr.is_floating_point():
        raise TypeError("edge_attr must be a floating-point tensor")
    if edge_attr.device != x.device:
        raise ValueError("edge_attr must be on the same device as x")


class DenseGraphAttention(nn.Module):
    """Pure-Torch GATv2-style attention with optional edge conditioning.

    With edge features enabled, ``None`` uses node-only attention for that call.
    With the flag disabled, attributes are ignored and legacy math is unchanged.
    """
    def __init__(self, in_dim, out_dim, heads=4, dropout=0.1,
                 edge_attr_dim=None, use_edge_features=False):
        super().__init__(); self.heads=heads; self.out_dim=out_dim
        _validate_edge_configuration(edge_attr_dim, use_edge_features)
        self.edge_attr_dim=edge_attr_dim; self.use_edge_features=use_edge_features
        self.lin=nn.Linear(in_dim,heads*out_dim,bias=False)
        self.att=nn.Parameter(torch.empty(heads,out_dim))
        nn.init.xavier_uniform_(self.att)
        self.leaky_relu=nn.LeakyReLU(.2)
        self.dropout=nn.Dropout(dropout); self.act=nn.ELU()
        if use_edge_features:
            self.edge_proj=nn.Linear(edge_attr_dim,heads,bias=False)
    def forward(self,x,edge_index,edge_attr=None,return_attention_weights=False):
        if self.use_edge_features:
            _validate_edge_attr(x,edge_index,edge_attr,self.edge_attr_dim)
        n=x.size(0); h=self.lin(x).view(n,self.heads,self.out_dim)
        out=torch.zeros_like(h)
        # Match PyG's default self-loop behavior so isolated nodes retain their
        # transformed state. Zero is the training-mean edge vector after the
        # required normalization and is neutral for fallback self-loops.
        loops=torch.arange(n,device=edge_index.device,dtype=edge_index.dtype)
        indices=torch.cat((edge_index,torch.stack((loops,loops))),dim=1)
        src,dst=indices
        weights=x.new_zeros((indices.size(1),self.heads)) if return_attention_weights else None
        edge_scores = (
            self.edge_proj(edge_attr)
            if self.use_edge_features and edge_attr is not None else None
        )
        for d in range(n):
            idx=(dst==d).nonzero(as_tuple=False).flatten()
            if idx.numel()==0: continue
            s=src[idx]
            # GATv2 applies its non-linearity before the learned attention
            # vector. Summing separate scalar projections makes the ranking
            # static with respect to the destination node.
            scores=(self.leaky_relu(h[s]+h[d])*self.att).sum(dim=-1)
            if edge_scores is not None:
                original=idx < edge_index.size(1)
                scores[original]=scores[original]+edge_scores[idx[original]]
            alpha=torch.softmax(scores,dim=0).unsqueeze(-1)
            if return_attention_weights: weights[idx]=alpha.squeeze(-1)
            out[d]=torch.sum(alpha*h[s],dim=0)
        result=self.act(self.dropout(out)).mean(1)
        return (result,(indices,weights)) if return_attention_weights else result

class GATv2GraphEncoder(nn.Module):
    """Two attention layers with opt-in edge conditioning in both backends.

    ``edge_attr`` may be omitted even when conditioning is enabled, in which case
    both layers use node-only attention. The disabled configuration retains the
    legacy parameters, initialization order, and forward operations.
    """
    def __init__(self,node_dim,hidden_dim=128,out_dim=128,heads=4,dropout=0.1,
                 edge_attr_dim=None,use_edge_features=False):
        super().__init__(); self.has_pyg=HAS_PYG
        _validate_edge_configuration(edge_attr_dim,use_edge_features)
        self.edge_attr_dim=edge_attr_dim; self.use_edge_features=use_edge_features
        if HAS_PYG:
            edge_dim=edge_attr_dim if use_edge_features else None
            self.conv1=GATv2Conv(node_dim,hidden_dim,heads=heads,concat=False,dropout=dropout,edge_dim=edge_dim)
            self.conv2=GATv2Conv(hidden_dim,out_dim,heads=heads,concat=False,dropout=dropout,edge_dim=edge_dim)
        else:
            self.conv1=DenseGraphAttention(node_dim,hidden_dim,heads,dropout,edge_attr_dim,use_edge_features)
            self.conv2=DenseGraphAttention(hidden_dim,out_dim,heads,dropout,edge_attr_dim,use_edge_features)
        self.norm1=nn.LayerNorm(hidden_dim); self.norm2=nn.LayerNorm(out_dim)
        self.act=nn.GELU(); self.dropout=nn.Dropout(dropout)
    def forward(self,x,edge_index,edge_attr=None):
        if self.use_edge_features:
            _validate_edge_attr(x,edge_index,edge_attr,self.edge_attr_dim)
            h=self.act(self.conv1(x,edge_index,edge_attr=edge_attr)); h=self.norm1(h); h=self.dropout(h)
            h=self.act(self.conv2(h,edge_index,edge_attr=edge_attr)); h=self.norm2(h)
        else:
            h=self.act(self.conv1(x,edge_index)); h=self.norm1(h); h=self.dropout(h)
            h=self.act(self.conv2(h,edge_index)); h=self.norm2(h)
        # State pooling: mean + max gives a stable graph-level representation.
        return torch.cat([h.mean(dim=0),h.max(dim=0).values],dim=-1)

    @torch.no_grad()
    def attention_weights(self,x,edge_index,edge_attr=None):
        """Actual per-head layer coefficients; caller must use evaluation mode.

        Returned indices include PyG's automatic self-loops. Consumers must
        exclude those before matching coefficients to observed edge features.
        """
        if self.training:
            raise ValueError('attention diagnostics require evaluation mode')
        if self.use_edge_features:
            _validate_edge_attr(x,edge_index,edge_attr,self.edge_attr_dim)
        attributes=edge_attr if self.use_edge_features else None
        h,first=self.conv1(x,edge_index,edge_attr=attributes,return_attention_weights=True)
        h=self.dropout(self.norm1(self.act(h)))
        _,second=self.conv2(h,edge_index,edge_attr=attributes,return_attention_weights=True)
        return [first,second]
