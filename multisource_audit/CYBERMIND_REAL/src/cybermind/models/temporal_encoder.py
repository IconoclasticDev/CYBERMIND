from __future__ import annotations
import torch
from torch import nn

class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self,d_model,max_len=512):
        super().__init__(); pe=torch.zeros(max_len,d_model); pos=torch.arange(max_len).unsqueeze(1).float()
        div=torch.exp(torch.arange(0,d_model,2).float()*(-torch.log(torch.tensor(10000.0))/d_model))
        pe[:,0::2]=torch.sin(pos*div); pe[:,1::2]=torch.cos(pos*div); self.register_buffer('pe',pe.unsqueeze(0))
    def forward(self,x): return x + self.pe[:,:x.size(1)]

class TemporalTransformerEncoder(nn.Module):
    def __init__(self,input_dim,model_dim=256,nhead=8,layers=4,dropout=0.1):
        super().__init__(); self.proj=nn.Linear(input_dim,model_dim); self.pos=SinusoidalPositionalEncoding(model_dim)
        layer=nn.TransformerEncoderLayer(model_dim,nhead,model_dim*4,dropout,batch_first=True,norm_first=True,activation='gelu')
        self.encoder=nn.TransformerEncoder(layer,num_layers=layers,norm=nn.LayerNorm(model_dim))
    def forward(self,x): return self.encoder(self.pos(self.proj(x)))
