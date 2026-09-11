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

def mutate_state(state, intervention: Intervention):
    s=copy.deepcopy(state)
    if intervention.action in ('Block Host','Isolate Host') and intervention.host is not None:
        h=intervention.host
        s.x[h] = s.x[h] * (0.05 if intervention.action=='Isolate Host' else 0.15)
        mask=(s.edge_index[0]!=h)&(s.edge_index[1]!=h)
        s.edge_index=s.edge_index[:,mask]
        s.edge_attr=s.edge_attr[mask]
    elif intervention.action=='Block Port' and intervention.port is not None and s.edge_attr.numel():
        mask=(s.edge_attr[:,3].round().long()!=int(intervention.port))
        s.edge_index=s.edge_index[:,mask]; s.edge_attr=s.edge_attr[mask]
    elif intervention.action=='Restrict Edge' and intervention.edge is not None and s.edge_attr.numel():
        a,b=intervention.edge; mask=~((s.edge_index[0]==a)&(s.edge_index[1]==b)); s.edge_attr[~mask]*=intervention.factor
    elif intervention.action=='Rate Limit':
        s.x[:,0:4]*=intervention.factor
    return s

def attack_gravity(model,state,k=4,hosts=None,device='cpu'):
    model.eval(); state.x=state.x.to(device); state.edge_index=state.edge_index.to(device); state.edge_attr=state.edge_attr.to(device)
    with torch.no_grad():
        base=model.forecast([state],k,seed=0,explain=False)['infiltration_probability'][-1].item()
        hosts=list(range(state.x.size(0))) if hosts is None else hosts
        out=[]
        for h in hosts:
            cf=mutate_state(state,Intervention('Isolate Host',host=h))
            p=model.forecast([cf],k,seed=0,explain=False)['infiltration_probability'][-1].item()
            out.append({'host':state.node_ids[h],'index':h,'baseline_risk':base,'counterfactual_risk':p,'attack_gravity':base-p})
    return sorted(out,key=lambda x:x['attack_gravity'],reverse=True)

def rank_interventions(model,state,k=4,hosts=None,ports=None,device='cpu'):
    results=[]
    hosts=list(range(state.x.size(0))) if hosts is None else hosts
    ports=[] if ports is None else ports
    actions=[Intervention('No Action')]+[Intervention('Isolate Host',host=h) for h in hosts]
    actions += [Intervention('Block Port',port=p) for p in ports]
    model.eval();
    for a in actions:
        cf=mutate_state(state,a)
        with torch.no_grad(): risk=model.forecast([cf],k,seed=0,explain=False)['infiltration_probability'][-1].item()
        results.append({'action':a.action,'host':a.host,'port':a.port,'future_risk':risk})
    results.sort(key=lambda x:x['future_risk'])
    return results
