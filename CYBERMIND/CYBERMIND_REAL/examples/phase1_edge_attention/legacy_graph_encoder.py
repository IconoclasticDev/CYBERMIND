from __future__ import annotations
import torch
from torch import nn

try:
    from torch_geometric.nn import GATv2Conv
    HAS_PYG = True
except Exception:
    GATv2Conv = None
    HAS_PYG = False

class DenseGraphAttention(nn.Module):
    """Pure-Torch fallback with the same role as GATv2 for environments without PyG."""
    def __init__(self, in_dim, out_dim, heads=4, dropout=0.1):
        super().__init__(); self.heads=heads; self.out_dim=out_dim
        self.lin=nn.Linear(in_dim,heads*out_dim,bias=False)
        self.q=nn.Linear(out_dim,1,bias=False); self.k=nn.Linear(out_dim,1,bias=False)
        self.dropout=nn.Dropout(dropout); self.act=nn.ELU()
    def forward(self,x,edge_index):
        n=x.size(0); h=self.lin(x).view(n,self.heads,self.out_dim)
        out=torch.zeros_like(h)
        if edge_index.numel()==0: return out.mean(1)
        src,dst=edge_index
        for d in range(n):
            idx=(dst==d).nonzero(as_tuple=False).flatten()
            if idx.numel()==0: continue
            s=src[idx]
            scores=(self.q(h[s])+self.k(h[d])).squeeze(-1)
            alpha=torch.softmax(scores,dim=0).unsqueeze(-1)
            out[d]=torch.sum(alpha*h[s],dim=0)
        return self.act(self.dropout(out)).mean(1)

class GATv2GraphEncoder(nn.Module):
    def __init__(self,node_dim,hidden_dim=128,out_dim=128,heads=4,dropout=0.1):
        super().__init__(); self.has_pyg=HAS_PYG
        if HAS_PYG:
            self.conv1=GATv2Conv(node_dim,hidden_dim,heads=heads,concat=False,dropout=dropout,edge_dim=None)
            self.conv2=GATv2Conv(hidden_dim,out_dim,heads=heads,concat=False,dropout=dropout,edge_dim=None)
        else:
            self.conv1=DenseGraphAttention(node_dim,hidden_dim,heads,dropout)
            self.conv2=DenseGraphAttention(hidden_dim,out_dim,heads,dropout)
        self.norm1=nn.LayerNorm(hidden_dim); self.norm2=nn.LayerNorm(out_dim)
        self.act=nn.GELU(); self.dropout=nn.Dropout(dropout)
    def forward(self,x,edge_index):
        h=self.act(self.conv1(x,edge_index)); h=self.norm1(h); h=self.dropout(h)
        h=self.act(self.conv2(h,edge_index)); h=self.norm2(h)
        # State pooling: mean + max gives a stable graph-level representation.
        return torch.cat([h.mean(dim=0),h.max(dim=0).values],dim=-1)
