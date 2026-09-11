from __future__ import annotations
import torch

def gradient_feature_attribution(model,state,k=4,topk=10):
    model.eval(); x=state.x.detach().clone().requires_grad_(True)
    s=type(state)(x=x,edge_index=state.edge_index,edge_attr=state.edge_attr,node_ids=state.node_ids,timestamp=state.timestamp,
                  y_infiltration=state.y_infiltration,y_stage=state.y_stage,scenario_id=state.scenario_id,attack_label=state.attack_label,metadata=state.metadata)
    out=model.forecast([s],k); score=torch.sigmoid(out['infiltration_logits'][:,-1]).sum(); model.zero_grad(set_to_none=True); score.backward()
    a=(x.grad.abs()*x.abs()).mean(dim=0).detach().cpu()
    names=['packet_count','flow_count','bytes_total','packets_total','unique_peer_count','unique_dst_port_count','tcp_ratio','udp_ratio','mean_duration','mean_iat','bytes_per_flow','packets_per_flow','activity_rate','anomaly_proxy']
    vals=[{'feature':names[i],'attribution':float(a[i])} for i in range(min(len(names),len(a)))]
    return sorted(vals,key=lambda z:z['attribution'],reverse=True)[:topk]
