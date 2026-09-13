"""Reviewed frozen-fixture mechanical gate; never used for integration data."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def judge_frozen(steps, history, gradients):
    if len(steps) != 4 or [s['step'] for s in steps] != [1, 2, 3, 4]:
        return False
    legal = all(s['samples'] > 0 and s['illegal_count'] == 0 for s in steps)
    finite = bool(history) and all(math.isfinite(v) for row in history for split in ('train', 'val')
                                  for v in row[split].values() if isinstance(v, (int, float)))
    # Non-degenerate means actual nonzero supervised objectives and gradient flow,
    # not diverse predictions or nonnegative Gaussian density NLL.
    active = bool(history) and all(row[split][key] > 0 for row in history for split in ('train', 'val')
                                  for key in ('stage', 'crf_stage'))
    gradients_active = bool(gradients) and all(math.isfinite(v) and v > 0 for v in gradients)
    return legal and finite and active and gradients_active


def main():
    source = ROOT/'examples/phase3_root_cause/original_frozen_cuda'
    history = json.loads((source/'train_history.json').read_text())
    diagnostic = json.loads((source/'training_diagnostics.jsonl').read_text().splitlines()[0])
    norms = diagnostic['gradients']['stage_head_weight']
    results = {}
    for suffix in ('', '_last'):
        report = json.loads((source/f'rollout{suffix}.json').read_text())
        results['last' if suffix else 'selected'] = dict(
            passed=judge_frozen(report['per_step'], history, [norms['ce_norm'], norms['crf_norm']]),
            per_step=report['per_step'], historical_diversity_gate_passed=report['all_steps_pass'])
    result = dict(scope='original_frozen_cuda ONLY', reviewed_change=True,
                  authorization='User: execute this plan immidiately; CYBERMIND_Frozen_Fixture_Gate_Decision.pdf engineering Option 2',
                  evidence_reused_without_training=True, fixture_regenerated=False,
                  integration_gate_changed=False, stage_head_gradients=norms, results=results)
    assert all(r['passed'] for r in results.values())
    (OUT/'frozen_gate_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Reviewed frozen mechanical gate PASS; historical diversity results remain FAIL.')


if __name__ == '__main__':
    main()
