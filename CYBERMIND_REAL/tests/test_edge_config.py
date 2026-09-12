"""The edge flag and inferred width must survive checkpoint reconstruction."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.utils.config import edge_model_kwargs


def test_legacy_config_and_observed_dimension():
    assert edge_model_kwargs({}) == {'use_edge_features': False, 'edge_attr_dim': None}
    assert edge_model_kwargs({'use_edge_features': True}, observed_edge_dim=27) == {
        'use_edge_features': True, 'edge_attr_dim': 27}


def test_checkpoint_recovers_inferred_width():
    checkpoint = {'use_edge_features': True, 'edge_attr_dim': 7}
    assert edge_model_kwargs({'use_edge_features': True}, checkpoint) == checkpoint
    assert edge_model_kwargs({}, checkpoint) == checkpoint


@pytest.mark.parametrize('cfg,checkpoint,observed', [
    ({'use_edge_features': 'false'}, {}, None),
    ({'use_edge_features': True}, {}, None),
    ({'use_edge_features': True, 'edge_attr_dim': 7}, {}, 27),
    ({'use_edge_features': True, 'edge_attr_dim': 7}, {'use_edge_features': True, 'edge_attr_dim': 27}, None),
    ({'use_edge_features': False}, {'use_edge_features': True, 'edge_attr_dim': 27}, None),
])
def test_incompatible_edge_architecture_rejected(cfg, checkpoint, observed):
    with pytest.raises(ValueError):
        edge_model_kwargs(cfg, checkpoint, observed)
