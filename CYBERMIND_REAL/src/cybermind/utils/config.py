from pathlib import Path
import yaml

def load_config(path):
    with open(path,'r',encoding='utf-8') as f: return yaml.safe_load(f)


def edge_model_kwargs(model_config, checkpoint_config=None, observed_edge_dim=None):
    """Resolve the optional edge architecture without changing legacy checkpoints.

    Training infers the width from real graph tensors and persists it in the
    checkpoint config. Inference can recover that width when the run YAML omits it.
    Explicit incompatible flags or widths must not silently load a different model.
    """
    checkpoint_config = checkpoint_config or {}
    enabled = model_config.get('use_edge_features', checkpoint_config.get('use_edge_features', False))
    if not isinstance(enabled, bool):
        raise ValueError('model.use_edge_features must be a YAML boolean.')
    if 'use_edge_features' in checkpoint_config and enabled != checkpoint_config['use_edge_features']:
        raise ValueError('Edge feature flag does not match the checkpoint architecture.')
    if not enabled:
        return {'use_edge_features': False, 'edge_attr_dim': None}
    width = model_config.get('edge_attr_dim', checkpoint_config.get('edge_attr_dim', observed_edge_dim))
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError('Enabled edge features require a positive model.edge_attr_dim or observed graph width.')
    for expected in (observed_edge_dim, checkpoint_config.get('edge_attr_dim')):
        if expected is not None and width != expected:
            raise ValueError('Configured edge_attr_dim does not match graph/checkpoint edge width.')
    return {'use_edge_features': True, 'edge_attr_dim': width}


def stage_model_kwargs(config, checkpoint_config=None):
    """One loss flag controls both the trained CRF and checkpoint decoding."""
    checkpoint_loss = (checkpoint_config or {}).get('loss', {})
    enabled = config.get('loss', {}).get('use_crf_stage', checkpoint_loss.get('use_crf_stage', False))
    if not isinstance(enabled, bool):
        raise ValueError('loss.use_crf_stage must be a YAML boolean.')
    if checkpoint_config is not None and enabled != checkpoint_loss.get('use_crf_stage', False):
        raise ValueError('CRF stage flag does not match the checkpoint architecture.')
    return {'use_crf_stage': enabled}
