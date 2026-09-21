"""Reproduce and decompose historical isolation without changing its evidence."""
import copy
import json
from pathlib import Path
import sys
import torch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.analyst.view import load_case
from cybermind.counterfactual.simulator import mutate_state, Intervention

torch.set_num_threads(2)
checkpoint = ROOT / 'examples/phase3_third_round/extended200/checkpoints/combined.pt'
model, cfg, sample, lineage, _ = load_case(checkpoint, ROOT, 0)
ck = torch.load(checkpoint, map_location='cpu', weights_only=False)
observed = sample.states[:-1]
original = observed[-1]
scaled = copy.deepcopy(original)
scaled.x[0] *= .05
edges = copy.deepcopy(original)
keep = (edges.edge_index[0] != 0) & (edges.edge_index[1] != 0)
edges.edge_index = edges.edge_index[:, keep]
edges.edge_attr = edges.edge_attr[keep]
legacy = copy.deepcopy(edges)
legacy.x[0] *= .05
variants = {'baseline': original, 'legacy_scaling_only': scaled,
            'edge_cut_only': edges, 'legacy_combined': legacy,
            'current_implementation': mutate_state(original, Intervention('Isolate Host', host=0))}
results = {}
for name, state in variants.items():
    results[name] = {}
    for draws, seeds in ((4, [0]), (512, list(range(10)))):
        values = []
        for seed in seeds:
            with torch.no_grad():
                out = model.forecast(observed[:-1] + [state], 4, n_rollouts=draws, seed=seed, explain=False)
            values.append({'seed': seed, 'risks': out['infiltration_probability'].tolist(),
                           'final_variance': float(out['infiltration_variance'][-1])})
        results[name][str(draws)] = values
    results[name]['edge_index'] = state.edge_index.tolist()
    results[name]['edge_attr'] = state.edge_attr.tolist()
    results[name]['normalized_node_features'] = state.x.tolist()
    mean = torch.tensor(ck['normalization']['node']['mean'])
    std = torch.tensor(ck['normalization']['node']['std'])
    results[name]['reconstructed_raw_node_features'] = (state.x * std + mean).tolist()
    results[name]['periodic_features'] = model.periodic_input(state.x)[:, -2:].tolist()
report = {'lineage': lineage, 'host_index': 0, 'horizon': 4,
          'feature_names': ck['normalization']['node']['features'],
          'interpretation': 'Paired seeds and draws; edge cut and scaled normalized features evaluated independently.',
          'results': results}
output = Path(__file__).with_name(sys.argv[1] if len(sys.argv) > 1 else 'before.json')
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
for name, value in results.items():
    print(name, '4 draws seed0', value['4'][0]['risks'][-1],
          '512 draws mean', sum(v['risks'][-1] for v in value['512']) / 10)
