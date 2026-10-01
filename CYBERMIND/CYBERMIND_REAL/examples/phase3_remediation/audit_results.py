"""Independently count unchanged four-step gates and verify frozen evidence."""
from pathlib import Path
import importlib.util
import json
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
GIT = r'C:\Users\as030\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
spec = importlib.util.spec_from_file_location('preservation_helpers', ROOT/'examples/phase2_stage_decoder/run_verification.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def main():
    result = {'baseline': h.verify_baseline(), 'gates_changed': False, 'prototype_fixture_used': False}
    for group in ('phase3_joint', 'phase3_balanced_stage', 'phase3_root_cause'):
        folder = ROOT/'examples'/group
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'))
        counts = {}
        for category in ('files', 'local_untracked_tensors_and_checkpoints'):
            for name, expected in manifest[category].items():
                assert h.fingerprint(folder/name) == expected, (group, name)
            counts[category] = len(manifest[category])
        result[group] = counts
    protected = ['configs/gb10_edge_only.yaml', 'configs/gb10_crf_only.yaml', 'configs/gb10_baseline.yaml']
    changes = subprocess.check_output([GIT, 'diff', '38d0449', '--', *protected], cwd=ROOT, text=True)
    untracked = subprocess.check_output([GIT, 'ls-files', '--others', '--exclude-standard', '--', *protected], cwd=ROOT, text=True)
    assert not changes and not untracked
    result['protected_phase4_configs_unchanged'] = True
    cases = {}
    for path in sorted(OUT.glob('*/status.json')):
        status = json.loads(path.read_text(encoding='utf-8'))
        assert status['execution'] == 'complete' and status['epochs_completed'] == 100
        cases[path.parent.name] = {}
        for suffix in ('', '_last'):
            report = json.loads((path.parent/f'rollout{suffix}.json').read_text(encoding='utf-8'))
            assert len(report['per_step']) == 4
            passed = []
            for t in range(1, 5):
                stages = [row['steps'][t]['decoded_stage'] for row in report['samples']]
                prior = [row['steps'][t-1]['decoded_stage'] for row in report['samples']]
                assert all(0 <= s <= 6 for s in stages + prior)
                illegal = sum(b < a and a != 6 and b != 6 for a, b in zip(prior, stages))
                distinct = len(set(stages) - {6})
                unknown = stages.count(6)
                summary = report['per_step'][t-1]
                assert (summary['illegal_count'], summary['distinct_non_unknown'], summary['unknown_count']) == (illegal, distinct, unknown)
                gate = illegal == 0 and distinct >= 2 and unknown < len(stages)
                assert summary['passed'] == gate
                passed.append(gate)
            assert report['all_steps_pass'] == all(passed)
            cases[path.parent.name]['last' if suffix else 'selected'] = {'epoch': report['selected_epoch'], 'per_step_pass': passed}
    assert len(cases) == 8
    result['independently_counted_cases'] = cases
    (OUT/'preservation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
