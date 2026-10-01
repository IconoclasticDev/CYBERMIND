"""Audit recorded Phase 3 evidence; an unmet diversity gate cannot pass silently."""
from pathlib import Path
import importlib.util
import json
import math
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('helpers', ROOT / 'examples/phase2_stage_decoder/run_verification.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    matrix = []
    count = 0
    for variant, edge, crf in [('baseline',0,0),('edge_only',1,0),('crf_only',0,1),('combined',1,1)]:
        cases = list(ET.parse(OUT / f'pytest_{variant}.xml').iter('testcase'))
        assert len(cases) == 96
        assert not any(case.find(tag) is not None for case in cases for tag in ('failure','error','skipped'))
        count += len(cases)
        for device in ('cpu','cuda'):
            name = f'test_joint_feature_execution_matrix[edges-{edge}-crf-{crf}-{device}]'
            matching = [case for case in cases if case.attrib['name'] == name]
            assert len(matching) == 1, name
            props = {p.attrib['name']: p.attrib['value'] for p in matching[0].findall('./properties/property')}
            assert props['device'] == device
            assert props['use_edge_features'] == str(bool(edge)) and props['use_crf_stage'] == str(bool(crf))
            assert props['strict_checkpoint_reload'] == props['all_gradients_finite'] == 'True'
            assert math.isfinite(float(props['joint_loss']))
            for key in (['conv1_edge_gradient_norm','conv2_edge_gradient_norm'] if edge else []) + (['crf_transition_gradient_norm'] if crf else []):
                assert math.isfinite(float(props[key])) and float(props[key]) > 0
            if crf:
                assert float(props['forecast_illegal_transition_rate']) == 0
            matrix.append(dict(variant=variant, name=name, properties=props))
    for filename in ('eval_test.json','train_history.json'):
        helpers.compare_legacy(read(OUT/'baseline'/filename), read(helpers.BASELINE/'integration'/filename))
    helpers.compare_legacy(read(OUT/'legacy_eval.json'), read(helpers.BASELINE/'eval_test.json'))
    memory = {}
    for variant in ('combined_cuda','smoke_combined_cuda'):
        history = read(OUT/variant/'train_history.json')
        assert len(history) == 2
        assert all(math.isfinite(v) for epoch in history for split in ('train','val') for v in epoch[split].values() if isinstance(v,(float,int)))
        memory[variant] = read(OUT/variant/'train_memory.json')
        assert memory[variant]['status'] == 'passed' and memory[variant]['below_device_vram'] is True
        assert 0 < memory[variant]['peak_allocated_bytes'] <= memory[variant]['peak_reserved_bytes'] < memory[variant]['ceiling_bytes']
    diagnosis = read(OUT/'collapse_diagnosis.json')
    diversity_passed = all(not row['decoded_single_stage'] for row in diagnosis['results'] if row['variant'] in ('combined_cuda','smoke_combined_cuda'))
    audit = dict(phase=3, status='passed' if diversity_passed else 'incomplete_diversity_gate',
                 test_executions_passed=count, test_executions_skipped=0,
                 joint_cases=matrix, both_off_regression_within_1e_6=True,
                 gpu_two_epoch_runs_finite=True, gpu_memory=memory,
                 baseline=helpers.verify_baseline(), prediction_diversity_passed=diversity_passed,
                 phase4_authorized=False,
                 unresolved=['Phase 3.3 rejects zero illegal transitions although Phase 2 requires hard constraints.',
                             'Both smoke fixtures produce single-stage raw emissions and decoded predictions after two epochs.'] if not diversity_passed else [])
    (OUT/'audit_status.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(audit['status'], count, 'test executions passed')


if __name__ == '__main__':
    main()
