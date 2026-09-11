from __future__ import annotations
import torch
from torch import nn
from .graph_encoder import GATv2GraphEncoder
from .temporal_encoder import TemporalTransformerEncoder
from .dynamics import DynamicsModel
from .heads import FutureStateHead,InfiltrationHead,StageHead

class WorldModel(nn.Module):
    def __init__(self,node_dim,graph_hidden=128,graph_out=128,temporal_dim=256,nhead=8,temporal_layers=4,num_stages=4,dropout=.1):
        super().__init__(); self.graph=GATv2GraphEncoder(node_dim,graph_hidden,graph_out,heads=4,dropout=dropout)
        graph_repr=graph_out*2
        self.temporal=TemporalTransformerEncoder(graph_repr,temporal_dim,nhead,temporal_layers,dropout)
        self.to_latent=nn.Linear(temporal_dim,temporal_dim)
        self.dynamics=DynamicsModel(temporal_dim)
        self.state_head=FutureStateHead(temporal_dim)
        self.infiltration_head=InfiltrationHead(temporal_dim)
        self.stage_head=StageHead(temporal_dim,num_stages)
    def encode_state(self,state): return self.graph(state.x,state.edge_index)
    def encode_sequence(self,states): return torch.stack([self.encode_state(s) for s in states],dim=0)
    def encode_batch_sequences(self,batch_states): return torch.stack([self.encode_sequence(states) for states in batch_states],dim=0)
    def forward(self,states):
        g=self.encode_sequence(states).unsqueeze(0)
        t=self.temporal(g).squeeze(0); z=self.to_latent(t)
        return {'graph_embeddings':g.squeeze(0),'temporal_latents':z,'next_latents':self.dynamics(z[:-1]) if z.size(0)>1 else z[:0]}
    def forward_batch(self,batch_states):
        # batch_states: list[list[GraphState]], each inner sequence may have different graph sizes.
        g=self.encode_batch_sequences(batch_states)
        t=self.temporal(g); z=self.to_latent(t)
        return {'graph_embeddings':g,'temporal_latents':z,'next_latents':self.dynamics(z[:,:-1]) if z.size(1)>1 else z[:,:0]}
    def rollout_from_latent(self,z0,steps):
        zs=self.dynamics.rollout(z0,steps)
        return {'latent':zs,'infiltration_logits':self.infiltration_head(zs),'stage_logits':self.stage_head(zs),'future_state':self.state_head(zs)}
    def forecast(self,states,k=4):
        out=self.forward(states); z0=out['temporal_latents'][-1]; return self.rollout_from_latent(z0,k)
