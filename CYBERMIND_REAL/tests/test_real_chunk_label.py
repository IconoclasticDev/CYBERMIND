import pandas as pd

from cybermind.data.real_chunk_label import corrected_labels, original_labels, stage_for_label


def rows(items):
    base = dict(src='1.1.1.1', dst='2.2.2.2', src_port=1234, dst_port=443,
                payload_size_max=10, capture_date='2018-02-14')
    return pd.DataFrame([{**base, **item} for item in items])


def test_corrected_rules_use_inclusive_session_start_and_attempted_precedence():
    frame = rows([
        dict(session_start='2018-02-14T18:01:50Z', src='13.58.98.64',
             dst='172.31.69.25', dst_port=22, payload_size_max=20),
        dict(session_start='2018-02-14T19:32:30Z', src='13.58.98.64',
             dst='172.31.69.25', dst_port=22, payload_size_max=0),
        dict(session_start='2018-02-14T19:32:30.000001Z', src='13.58.98.64',
             dst='172.31.69.25', dst_port=22, payload_size_max=20),
    ])
    result = corrected_labels(frame)
    assert result.label.tolist() == ['SSH-BruteForce', 'SSH-BruteForce - Attempted', 'BENIGN']
    assert result.attempted_category.tolist() == [-1, 0, -1]
    assert stage_for_label(result.label).tolist() == [2, 2, 0]


def test_nmap_filters_source_port_68():
    frame = rows([
        dict(capture_date='2018-03-01', session_start='2018-03-01T14:09:49Z',
             src='172.31.69.13', dst='172.31.69.12', src_port=68, dst_port=67),
        dict(capture_date='2018-03-01', session_start='2018-03-01T14:09:49Z',
             src='172.31.69.13', dst='172.31.69.12', src_port=1234, dst_port=68),
    ])
    result = corrected_labels(frame)
    assert result.label.tolist() == ['BENIGN', 'Infiltration - NMAP Portscan']


def test_bot_biflow_refinements_are_flagged_not_invented():
    frame = rows([
        dict(capture_date='2018-03-02', session_start='2018-03-02T19:53:45Z',
             src='172.31.69.23', dst='18.219.211.138', payload_size_max=30),
        dict(capture_date='2018-03-02', session_start='2018-03-02T15:00:00Z',
             src='172.31.69.23', dst='18.219.211.138', payload_size_max=0),
    ])
    result = corrected_labels(frame)
    assert result.label.tolist() == ['Botnet Ares', 'Botnet Ares']
    assert result.corrected_refinement_status.tolist() == [
        'unresolved_missing_bwd_rst_flags', 'unresolved_missing_reverse_payload_total']


def test_original_table2_uses_attacker_to_victim_and_whole_finish_minute():
    frame = rows([
        dict(session_start='2018-02-14T16:09:59.9Z', src='18.221.219.4', dst='172.31.69.25'),
        dict(session_start='2018-02-14T16:10:00Z', src='18.221.219.4', dst='172.31.69.25'),
        dict(session_start='2018-02-14T15:00:00Z', src='172.31.69.25', dst='18.221.219.4'),
    ])
    result = original_labels(frame)
    assert result.original_cic_label.tolist() == ['FTP-BruteForce', 'BENIGN', 'BENIGN']
