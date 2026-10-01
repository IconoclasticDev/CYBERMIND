import json

import pytest

from cybermind.analyst.case_qa import answer_case_question
from cybermind.analyst.case_security import (
    create_account, decrypt_report, encrypt_report, verify_account)


def test_encrypted_case_round_trip_requires_password_and_rejects_tampering(tmp_path):
    account = tmp_path / 'account.json'
    password = 'correct horse battery staple'
    create_account(account, password)
    assert verify_account(account, password)
    assert not verify_account(account, 'incorrect password')
    with pytest.raises(FileExistsError):
        create_account(account, password)

    report = {'forecast': [{'step': 1, 'risk': .8}],
              'lineage': {'checkpoint_sha256': 'abc'}, 'observed_flows': []}
    sealed = encrypt_report(report, password)
    assert b'checkpoint_sha256' not in sealed
    assert decrypt_report(sealed, password) == report
    with pytest.raises(ValueError):
        decrypt_report(sealed, 'incorrect password')
    envelope = json.loads(sealed)
    envelope['ciphertext'] = envelope['ciphertext'][:-2] + 'AA'
    with pytest.raises(ValueError):
        decrypt_report(json.dumps(envelope).encode(), password)


def test_local_account_requires_a_substantial_password(tmp_path):
    with pytest.raises(ValueError):
        create_account(tmp_path / 'account.json', 'short')
    assert not (tmp_path / 'account.json').exists()


def test_case_questions_cite_report_fields_and_do_not_invent_attack_claims():
    report = {
        'forecast': [
            {'step': 0, 'risk': .1, 'reported_stage': 'Benign'},
            {'step': 1, 'risk': .8, 'reported_stage': 'Unknown/Ambiguous'},
        ],
        'observed_flows': [
            {'src': '10.0.0.1', 'src_port': 1000, 'dst': '10.0.0.2',
             'dst_port': 80, 'review_flag': True,
             'review_signal': 'sequential port access'},
        ],
        'lineage': {'dataset': 'capture.pcap', 'dataset_sha256': 'feed',
                    'checkpoint_sha256': 'beef'},
    }
    risk = answer_case_question('What is the next risk?', report)
    assert '+1: 80.0%' in risk['answer']
    assert 'forecast[1].risk' in risk['evidence']
    flows = answer_case_question('Why was this flow flagged?', report)
    assert '10.0.0.1:1000' in flows['answer']
    assert 'not per-flow model probabilities' in flows['answer']
    assert flows['evidence'] == ['observed_flows[0]']
    source = answer_case_question('What is the source file?', report)
    assert 'capture.pcap' in source['answer']
    stages = answer_case_question('Which stage?', report)
    assert 'Unknown/Ambiguous' in stages['answer']



def test_saved_case_comparison_reports_evidence_without_rescoring():
    from cybermind.analyst.case_qa import compare_case_reports
    first = {'lineage': {'dataset_sha256': 'a', 'sequence_index': 0},
             'forecast': [{'step': 1, 'risk': .2, 'reported_stage': 'Benign'}],
             'observed_flows': [{'review_flag': True}]}
    second = {'lineage': {'dataset_sha256': 'b', 'sequence_index': 4},
              'forecast': [{'step': 1, 'risk': .7, 'reported_stage': 'Unknown'}],
              'observed_flows': [{'review_flag': False}]}
    rows = {row['measure']: row for row in compare_case_reports(first, second)}
    assert rows['final_risk']['first_case'] == .2
    assert rows['final_risk']['second_case'] == .7
    assert rows['review_flagged_flows']['first_case'] == 1
    assert rows['input_sha256']['second_case'] == 'b'


def test_feature_range_check_is_explicitly_heuristic():
    import torch
    from cybermind.analyst.view import input_shift_summary
    from cybermind.data.types import GraphState
    state = GraphState(
        torch.tensor([[0.0, 7.0]]), torch.empty((2, 0), dtype=torch.long),
        torch.empty((0, 27)), ['host'], 0, 0, 0, 'scenario', 'UNLABELED',
        metadata={'normalization_fingerprint': 'training-normalizer'})
    result = input_shift_summary([state])
    assert result['available'] and result['exceeded_values'] == 1
    assert result['top_features'][0]['feature'] == 'node.flow_count'
    assert 'not a calibrated OOD detector' in result['limitation']


def test_combined_host_and_flow_question_cites_both_sources():
    from types import SimpleNamespace
    prior = SimpleNamespace(node_ids=['host-a'])
    latest = SimpleNamespace(node_ids=['host-a', 'host-b'])
    report = {'observed_flows': [{'src': 'host-a', 'dst': 'host-b',
                                  'review_flag': True, 'review_signal': 'TCP retransmissions'}]}
    answer = answer_case_question('Which hosts and flows changed?', report, [prior, latest])
    assert 'host-b' in answer['answer']
    assert 'TCP retransmissions' in answer['answer']
    assert 'observed_states[-1].node_ids' in answer['evidence']
    assert 'observed_flows[0]' in answer['evidence']
