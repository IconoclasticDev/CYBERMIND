"""Read-only checkpoint diagnosis; never tunes weights, labels or test thresholds."""
from collections import Counter
import json
from pathlib import Path
import sys
import torch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.dataset import GraphSequenceDataset
from cybermind.models.world_model import WorldModel
from cybermind.utils.config import edge_model_kwargs, stage_model_kwargs


def main():
    torch.set_num_threads(2)
    results = []
    for variant in ('baseline', 'combined', 'combined_cuda', 'smoke_combined_cuda'):
        checkpoints = sorted((OUT / variant / 'checkpoints').glob('*.pt'))
        for path in checkpoints:
            checkpoint = torch.load(path, map_location='cpu', weights_only=False)
            cfg = checkpoint['config']
            options = {k: cfg['model'][k] for k in ('graph_hidden','graph_out','temporal_dim','nhead','temporal_layers','num_stages','dropout')}
            options['graph_heads'] = cfg['model'].get('graph_heads', 8)
            model = WorldModel(checkpoint['node_dim'], **options, **edge_model_kwargs(cfg['model']),
                               **stage_model_kwargs(cfg)).eval()
            model.load_state_dict(checkpoint['model_state'])
            dataset = GraphSequenceDataset(ROOT / cfg['data']['processed_dir'] / 'test.pt')
            raw, decoded, labels = Counter(), Counter(), Counter()
            for sample in dataset:
                with torch.no_grad():
                    forecast = model.forecast(sample.states[:-1], 1, n_rollouts=cfg['eval'].get('n_rollouts',16),
                                              seed=cfg['eval'].get('rollout_seed',0), explain=False)
                    # latent_samples is [rollouts,time,dim]; exactly the mean raw
                    # StageHead emissions consumed by the CRF, before transitions.
                    emissions = model.stage_head(forecast['latent_samples']).float().mean(dim=0)
                raw.update(emissions.argmax(-1).tolist())
                decoded.update(forecast['decoded_stages'].tolist())
                labels.update([sample.states[-1].y_stage])
            train = GraphSequenceDataset(ROOT / cfg['data']['processed_dir'] / 'train.pt')
            train_labels = Counter(state.y_stage for sample in train for state in sample.states[1:])
            results.append(dict(variant=variant, checkpoint=path.relative_to(ROOT).as_posix(),
                                selected_epoch=checkpoint['epoch'], test_target_stage_histogram=dict(labels),
                                training_supervision_histogram=dict(train_labels),
                                raw_emission_argmax_histogram=dict(raw), decoded_histogram=dict(decoded),
                                raw_emissions_single_stage=len(raw)==1, decoded_single_stage=len(decoded)==1))
    (OUT / 'collapse_diagnosis.json').write_text(json.dumps({
        'synthetic_only': True, 'device': 'cpu', 'checkpoints_modified': False, 'results': results,
        'interpretation': 'Single-stage raw emissions already lack diversity before Viterbi. This does not prove useful stage learning; the Phase 3 diversity gate remains unmet.'
    }, indent=2), encoding='utf-8')
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    main()
