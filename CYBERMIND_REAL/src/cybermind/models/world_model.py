from __future__ import annotations
import torch
from torch import nn
from .graph_encoder import GATv2GraphEncoder
from .temporal_encoder import TemporalTransformerEncoder
from .dynamics import DynamicsModel
from .heads import FutureStateHead,InfiltrationHead,StageHead

class WorldModel(nn.Module):
    def __init__(self,node_dim,graph_hidden=128,graph_out=128,temporal_dim=256,nhead=8,temporal_layers=4,num_stages=7,dropout=.1,graph_heads=8):
        super().__init__(); self.graph=GATv2GraphEncoder(node_dim,graph_hidden,graph_out,heads=graph_heads,dropout=dropout)
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
    def forward(self,states,return_attention=False):
        g=self.encode_sequence(states).unsqueeze(0)
        temporal=self.temporal(g,return_attention=return_attention)
        t,attention=temporal if return_attention else (temporal,None)
        z=self.to_latent(t.squeeze(0))
        transition=self.dynamics(z[:-1])
        return {'graph_embeddings':g.squeeze(0),'temporal_latents':z,
                'next_latents':transition['mean'],'next_logvar':transition['logvar'],
                'temporal_attention':attention}
    def forward_batch(self,batch_states):
        # batch_states: list[list[GraphState]], each inner sequence may have different graph sizes.
        g=self.encode_batch_sequences(batch_states)
        t=self.temporal(g); z=self.to_latent(t)
        transition=self.dynamics(z[:,:-1])
        return {'graph_embeddings':g,'temporal_latents':z,
                'next_latents':transition['mean'],'next_logvar':transition['logvar']}
    def rollout_from_latent(self,z0,steps):
        zs=self.dynamics.rollout(z0,steps)
        return {'latent':zs,'infiltration_logits':self.infiltration_head(zs),'stage_logits':self.stage_head(zs),'future_state':self.state_head(zs)}
    def _forecast_core(self, states, k, n_rollouts, seed, return_attention=False):
        out = self.forward(states, return_attention=return_attention)
        z0 = out['temporal_latents'][-1]
        generator = torch.Generator(device=z0.device).manual_seed(seed)
        # Vectorize independent trajectories: [steps+1, rollouts, latent_dim].
        latent_samples = self.dynamics.rollout(z0.expand(n_rollouts, -1), k, generator=generator)
        risk_samples = self.infiltration_head(latent_samples).float().sigmoid()
        probabilities = risk_samples.mean(dim=1)
        stage_probabilities = self.stage_head(latent_samples).float().softmax(dim=-1).mean(dim=1)
        result = {
            'latent': latent_samples.mean(dim=1),
            'latent_samples': latent_samples.permute(1, 0, 2),
            'infiltration_logits': torch.logit(probabilities.clamp(1e-7, 1 - 1e-7)),
            'infiltration_probability': probabilities,
            'infiltration_variance': risk_samples.var(dim=1, unbiased=False),
            'rollout_probabilities': risk_samples.transpose(0, 1),
            'stage_logits': stage_probabilities.clamp_min(1e-7).log(),
            'future_state': self.state_head(latent_samples).mean(dim=1),
            'n_rollouts': n_rollouts, 'seed': seed,
        }
        return result, out['temporal_attention']

    def forecast(self, states, k=4, n_rollouts=16, seed=0, explain=True, topk=10):
        """Forecast with reproducible Gaussian rollouts and automatic explanations.

        Step zero is the observed latent; subsequent steps are stochastic futures.
        Variance is predictive dispersion, not a calibrated confidence decision.
        Internal perturbation probes use explain=False to avoid recursive work.
        """
        if not states or k < 0 or n_rollouts < 2:
            raise ValueError('forecast requires states, k >= 0 and n_rollouts >= 2')
        modes = [(module, module.training) for module in self.modules()]
        self.eval()
        try:
            result, attention = self._forecast_core(states, k, n_rollouts, seed, return_attention=explain)
            if explain:
                from cybermind.explainability.attribution import explain_forecast
                result['explanation'] = explain_forecast(
                    self, states, result, attention, k=k, n_rollouts=n_rollouts, seed=seed, topk=topk)
            return result
        finally:
            for module, training in modes:
                module.training = training
