from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import copy, torch

ACTIONS=('No Action','Block Host','Block Port','Isolate Host','Restrict Edge','Rate Limit')
@dataclass
class Intervention:
    action:str
    host:Optional[int]=None
    port:Optional[int]=None
    edge:Optional[tuple[int,int]]=None
    factor:float=0.25

def _normalizer_for(state, normalization):
    fingerprint=state.metadata.get('normalization_fingerprint')
    if not fingerprint:
        return None
    if normalization is None:
        raise ValueError('Raw-value intervention on normalized features requires checkpoint normalization')
    from cybermind.data.normalization import FeatureNormalizer
    normalizer=normalization if isinstance(normalization,FeatureNormalizer) else FeatureNormalizer(normalization)
    if normalizer.fingerprint != fingerprint:
        raise ValueError('Intervention normalization differs from the graph state')
    return normalizer


def mutate_state(state, intervention: Intervention, normalization=None):
    s=copy.deepcopy(state)
    if intervention.action in ('Block Host','Isolate Host') and intervention.host is not None:
        h=intervention.host
        if isinstance(h, bool) or not isinstance(h, int) or not 0 <= h < s.x.size(0):
            raise ValueError('Host must be a valid node index')
        # An edge-cut probe retains measured node features. Scaling normalized
        # features pulls raw values toward the training mean and fabricates a
        # post-containment measurement (including unrelated clock features).
        mask=(s.edge_index[0]!=h)&(s.edge_index[1]!=h)
        s.edge_index=s.edge_index[:,mask]
        s.edge_attr=s.edge_attr[mask]
    elif intervention.action=='Block Port' and intervention.port is not None and s.edge_attr.numel():
        normalizer=_normalizer_for(s,normalization)
        edge_raw=normalizer.inverse_transform(s.edge_attr,'edge') if normalizer else s.edge_attr
        mask=(edge_raw[:,3].round().long()!=int(intervention.port))
        s.edge_index=s.edge_index[:,mask]; s.edge_attr=s.edge_attr[mask]
    elif intervention.action=='Restrict Edge' and intervention.edge is not None and s.edge_attr.numel():
        normalizer=_normalizer_for(s,normalization)
        a,b=intervention.edge; selected=(s.edge_index[0]==a)&(s.edge_index[1]==b)
        edge_raw=normalizer.inverse_transform(s.edge_attr,'edge') if normalizer else s.edge_attr.clone()
        edge_raw[selected,0:2]*=intervention.factor
        s.edge_attr=normalizer.transform(edge_raw,'edge') if normalizer else edge_raw
    elif intervention.action=='Rate Limit':
        normalizer=_normalizer_for(s,normalization)
        node_raw=normalizer.inverse_transform(s.x,'node') if normalizer else s.x.clone()
        node_raw[:,0:4]*=intervention.factor
        s.x=normalizer.transform(node_raw,'node') if normalizer else node_raw
    return s

def attack_gravity(model,state,k=4,hosts=None,device='cpu',normalization=None):
    model.eval(); state.x=state.x.to(device); state.edge_index=state.edge_index.to(device); state.edge_attr=state.edge_attr.to(device)
    with torch.no_grad():
        base=model.forecast([state],k,seed=0,explain=False)['infiltration_probability'][-1].item()
        hosts=list(range(state.x.size(0))) if hosts is None else hosts
        out=[]
        for h in hosts:
            cf=mutate_state(state,Intervention('Isolate Host',host=h),normalization)
            p=model.forecast([cf],k,seed=0,explain=False)['infiltration_probability'][-1].item()
            out.append({'host':state.node_ids[h],'index':h,'baseline_risk':base,'counterfactual_risk':p,'attack_gravity':base-p})
    return sorted(out,key=lambda x:x['attack_gravity'],reverse=True)

def rank_interventions(model,state,k=4,hosts=None,ports=None,device='cpu',normalization=None):
    results=[]
    hosts=list(range(state.x.size(0))) if hosts is None else hosts
    ports=[] if ports is None else ports
    actions=[Intervention('No Action')]+[Intervention('Isolate Host',host=h) for h in hosts]
    actions += [Intervention('Block Port',port=p) for p in ports]
    model.eval();
    for a in actions:
        cf=mutate_state(state,a,normalization)
        with torch.no_grad(): risk=model.forecast([cf],k,seed=0,explain=False)['infiltration_probability'][-1].item()
        results.append({'action':a.action,'host':a.host,'port':a.port,'future_risk':risk})
    results.sort(key=lambda x:x['future_risk'])
    return results
