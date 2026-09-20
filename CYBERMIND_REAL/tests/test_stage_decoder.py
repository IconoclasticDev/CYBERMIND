"""Exact CRF checks and the Phase 2 CPU/CUDA gradient exit gate."""
import itertools
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.models.stage_decoder import StageDecoder
from cybermind.evaluation.metrics import illegal_transition_counts, illegal_transition_rate


def enumerate_paths(decoder, emissions, reset_mask=None):
    scores, paths = [], []
    for path in itertools.product(range(emissions.shape[-1]), repeat=len(emissions)):
        if any(not (decoder.allowed_transitions[a, b] or
                    (reset_mask is not None and reset_mask[t] and decoder.reset_transitions[a, b]))
               for t, (a, b) in enumerate(zip(path, path[1:]), 1)):
            continue
        score = sum(emissions[t, stage] for t, stage in enumerate(path))
        score = score + sum(decoder.transitions[a, b] for a, b in zip(path, path[1:]))
        paths.append(path)
        scores.append(score)
    return paths, torch.stack(scores)


@pytest.mark.parametrize('with_reset', [False, True])
def test_partition_nll_and_viterbi_match_exhaustive_paths(with_reset):
    decoder = StageDecoder(3, {'num_stages': 3,
        'transition_matrix': [[True, True, True], [False, True, True], [False, False, True]],
        'reset_transition_matrix': [[False, False, False], [True, False, False], [True, True, False]]})
    with torch.no_grad():
        decoder.transitions.copy_(torch.tensor([[.1, -.2, .3], [.4, -.5, .6], [.7, .8, -.9]]))
    emissions = torch.tensor([[.8, -.2, .1], [-.4, .3, .9], [.2, .7, -.6]])
    reset = torch.tensor([False, False, with_reset])
    paths, scores = enumerate_paths(decoder, emissions, reset)
    tags = torch.tensor(paths[2])
    expected_nll = torch.logsumexp(scores, dim=0) - scores[2]
    torch.testing.assert_close(decoder(emissions, tags, reset_mask=reset), expected_nll)
    assert tuple(decoder.decode(emissions, reset_mask=reset).tolist()) == paths[scores.argmax()]


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
def test_finite_loss_gradients_and_zero_illegal_decode(device, record_property):
    if device == 'cuda' and not torch.cuda.is_available():
        pytest.skip('CUDA unavailable; Phase 2 exit gate requires a GPU pass')
    torch.manual_seed(207)
    decoder = StageDecoder().to(device)
    emissions = torch.randn(3, 5, 7, device=device, requires_grad=True)
    tags = torch.tensor([[0, 1, 2, 3, 4], [2, 2, 3, 5, 6], [6, 0, 0, 1, 3]], device=device)
    loss = decoder(emissions, tags)
    loss.backward()
    assert torch.isfinite(loss)
    for name, gradient in [('emissions', emissions.grad), ('transitions', decoder.transitions.grad)]:
        assert gradient is not None and torch.isfinite(gradient).all()
        assert gradient.abs().sum() > 0
        record_property(name + '_gradient_norm', float(gradient.norm()))
    decoded = decoder.decode(emissions)
    assert illegal_transition_rate(decoded) == 0.0
    record_property('device', device)
    record_property('loss', float(loss.detach()))
    record_property('decoded_illegal_transition_rate', illegal_transition_rate(decoded))


@pytest.mark.parametrize('device',['cpu','cuda'])
def test_adversarial_independent_argmax_is_illegal_but_viterbi_is_legal(device,record_property):
    if device=='cuda' and not torch.cuda.is_available():
        pytest.skip('Phase 2 requires the adversarial decoder check on actual CUDA')
    emissions = torch.full((4, 7), -100.,device=device)
    emissions[range(4), [4, 2, 5, 1]] = 20.
    assert illegal_transition_rate(emissions.argmax(-1)) > 0
    decoded=StageDecoder().to(device).decode(emissions)
    assert illegal_transition_rate(decoded) == 0
    record_property('device',device)
    record_property('independent_argmax_rate',illegal_transition_rate(emissions.argmax(-1)))
    record_property('viterbi_rate',illegal_transition_rate(decoded))
    record_property('decoded_stages',decoded.tolist())


def test_explicit_reset_only_enables_backward_to_zero_or_one():
    decoder = StageDecoder()
    emissions = torch.full((3, 7), -100.)
    emissions[range(3), [4, 0, 1]] = 100.
    reset = torch.tensor([False, True, False])
    assert decoder.decode(emissions, reset_mask=reset).tolist() == [4, 0, 1]
    assert decoder.decode(emissions).tolist() != [4, 0, 1]
    assert torch.isfinite(decoder(emissions, torch.tensor([4, 0, 1]), reset_mask=reset))
    with pytest.raises(ValueError):
        decoder(emissions, torch.tensor([4, 2, 3]), reset_mask=reset)


def test_transition_loss_exclusion_splits_nll_without_changing_decode_policy():
    decoder = StageDecoder()
    torch.manual_seed(208)
    emissions = torch.randn(4, 7, requires_grad=True)
    tags = torch.tensor([1, 2, 0, 1])
    with pytest.raises(ValueError, match='illegal target'):
        decoder(emissions, tags)
    transition_loss_mask = torch.tensor([True, True, False, True])
    loss = decoder(emissions, tags, transition_loss_mask=transition_loss_mask)
    expected = decoder(emissions[:2], tags[:2]) + decoder(emissions[2:], tags[2:])
    torch.testing.assert_close(loss, expected)
    loss.backward()
    assert emissions.grad is not None and torch.isfinite(emissions.grad).all()
    decoded = decoder.decode(emissions.detach())
    assert illegal_transition_rate(decoded) == 0.0
    assert not decoder.allowed_transitions[2, 0]


def test_transition_loss_mask_rejects_false_first_entry():
    with pytest.raises(ValueError, match=r'\[:, 0\] must be true'):
        StageDecoder()(torch.zeros(2, 7), torch.tensor([0, 1]),
                       transition_loss_mask=torch.tensor([False, True]))


def test_unknown_is_exempt_and_illegal_supervision_fails():
    decoder = StageDecoder()
    emissions = torch.zeros(3, 7)
    assert torch.isfinite(decoder(emissions, torch.tensor([5, 6, 0])))
    assert illegal_transition_rate([5, 6, 0]) == 0
    with pytest.raises(ValueError):
        decoder(emissions, torch.tensor([5, 3, 4]))


def test_padding_and_one_step_batch_equal_individual_sequences():
    decoder = StageDecoder()
    torch.manual_seed(14)
    emissions = torch.randn(2, 3, 7)
    mask = torch.tensor([[True, True, True], [True, False, False]])
    tags = torch.tensor([[0, 1, 4], [3, -1, -1]])
    loss = decoder(emissions, tags, mask=mask)
    expected = (decoder(emissions[0], tags[0]) + decoder(emissions[1, :1], tags[1, :1])) / 2
    torch.testing.assert_close(loss, expected)
    decoded = decoder.decode(emissions, mask=mask)
    assert decoded[1, 1:].tolist() == [-1, -1]
    assert decoded[1, 0] == emissions[1, 0].argmax()
    torch.testing.assert_close(decoded[0], decoder.decode(emissions[0]))


@pytest.mark.parametrize('config', [
    {'num_stages': 7, 'transition_matrix': [[True]]},
    {'num_stages': 7, 'transition_matrix': [[False] * 7 for _ in range(7)]},
    {'num_stages': 3},
])
def test_invalid_config_rejected(config):
    with pytest.raises((ValueError, TypeError)):
        StageDecoder(7, config)


def test_reset_policy_cannot_enable_arbitrary_backward_jumps():
    resets = torch.zeros(7, 7, dtype=torch.bool)
    resets[5, 3] = True
    with pytest.raises(ValueError):
        StageDecoder(7, {'reset_transition_matrix': resets})


@pytest.mark.parametrize('mask', [torch.tensor([False, True]), torch.tensor([True, False, True])])
def test_nonprefix_or_empty_masks_rejected(mask):
    with pytest.raises(ValueError):
        StageDecoder().decode(torch.zeros(len(mask), 7), mask=mask)


def test_transition_metric_resets_padding_unknown_and_pooling():
    assert illegal_transition_counts([4, 0, 1], reset_mask=[False, True, False]) == {'illegal': 0, 'evaluated': 1}
    assert illegal_transition_counts([4, 2, 3], reset_mask=[False, True, False]) == {'illegal': 1, 'evaluated': 2}
    assert illegal_transition_rate([4, 0, 1]) == .5
    assert illegal_transition_rate([5, 6, 0]) == 0
    assert illegal_transition_counts([[0, 1, -1], [5, 2, 4]]) == {'illegal': 1, 'evaluated': 3}
    assert illegal_transition_rate([3]) == 0
    assert illegal_transition_rate([]) == 0
    assert illegal_transition_rate([-1, -1]) == 0
    assert illegal_transition_counts([0, 999, 1], mask=[True, False, True]) == {'illegal': 0, 'evaluated': 0}


@pytest.mark.parametrize('stages', [[7], [-2], [1.5]])
def test_transition_metric_rejects_invalid_ids(stages):
    with pytest.raises(ValueError):
        illegal_transition_rate(stages)
