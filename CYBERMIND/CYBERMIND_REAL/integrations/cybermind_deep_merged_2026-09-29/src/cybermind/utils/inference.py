"""Check preprocessed inference inputs against a checkpoint's feature contract."""
from cybermind.data.normalization import FeatureNormalizer


def verify_inference_states(checkpoint, states):
    constants = checkpoint.get('normalization')
    required = checkpoint.get('config', {}).get('data', {}).get('require_normalization', False)
    if required and constants is None:
        raise ValueError('Checkpoint is missing required training normalization constants.')
    expected = FeatureNormalizer(constants).fingerprint if constants else None
    for state in states:
        if state.x.size(-1) != checkpoint['node_dim']:
            raise ValueError('Inference feature width does not match checkpoint.')
        if expected and state.metadata.get('normalization_fingerprint') != expected:
            raise ValueError('Inference data normalization differs from checkpoint; reprocess with its training constants.')
