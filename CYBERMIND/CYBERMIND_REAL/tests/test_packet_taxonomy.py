import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cybermind.data.pcap_extract import pcap_to_dataframe, PACKET_FEATURES, _new_flow, _add_sequence
from cybermind.data.stages import classify_stage, STAGE_NAMES
from cybermind.data.adapters.unified import UnifiedAdapter
from scapy.all import IP, TCP, UDP, Raw, Ether, wrpcap


def capture(tmp_path, packets):
    target = tmp_path / 'test.pcap'
    for i, packet in enumerate(packets):
        packet.time = 1000.0 + i
    wrpcap(str(target), packets)
    return target


def test_packet_statistics_and_retransmissions(tmp_path):
    packets = [Ether()/IP(src='10.0.0.1', dst='10.0.0.2', ttl=ttl, flags='DF')/TCP(sport=1234, dport=80, seq=seq, flags='PA', window=window)/Raw(b'x'*size)
               for ttl, seq, window, size in [(64, 100, 1000, 10), (60, 110, 2000, 20), (62, 100, 3000, 10)]]
    row = pcap_to_dataframe(capture(tmp_path, packets), label='BENIGN').iloc[0]
    assert row.ttl_mean == 62
    assert row.ttl_variance == pytest.approx(8/3)
    assert row.tcp_window_mean == 2000
    assert row.tcp_window_variance == pytest.approx(2000000/3)
    assert row.ip_df_ratio == 1
    assert row.ip_fragment_ratio == 0
    assert row.payload_size_mean == pytest.approx(40/3)
    assert row.payload_size_variance == pytest.approx(200/9)
    assert (row.payload_size_min, row.payload_size_max, row.payload_size_p50) == (10, 20, 10)
    assert row.payload_size_p25 == 10
    assert row.payload_size_p75 == 15
    assert row.retransmission_count == 1
    assert row.retransmission_ratio == pytest.approx(1/3)
    assert row.infiltration == 0
    assert row.stage == 0
    assert row.packet_features_available == 1
    assert row.timestamp == pd.Timestamp(1002, unit='s')
    assert row.session_start == pd.Timestamp(1000, unit='s')
    assert np.isfinite(row[list(PACKET_FEATURES)].to_numpy(dtype=float)).all()


def test_fragment_flags(tmp_path):
    packets = [Ether()/IP(src='10.0.0.1', dst='10.0.0.2', proto=17, flags='MF', frag=1)/Raw(b'abcdefgh'),
               Ether()/IP(src='10.0.0.1', dst='10.0.0.2', proto=17, frag=2)/Raw(b'abcdefgh')]
    row = pcap_to_dataframe(capture(tmp_path, packets)).iloc[0]
    assert row.ip_mf_ratio == .5
    assert row.ip_fragment_ratio == 1
    assert row.tcp_window_mean == 0


@pytest.mark.parametrize('ports, sequential, randomized', [([80,81,82,83],1,0), ([80,443,22,3389],0,1), ([80,80,80,80],0,0)])
def test_port_access_patterns_no_future_leak(tmp_path, ports, sequential, randomized):
    packets = [Ether()/IP(src='10.0.0.1', dst='10.0.0.2')/TCP(sport=1234, dport=p, flags='S', seq=i) for i,p in enumerate(ports)]
    frame = pcap_to_dataframe(capture(tmp_path, packets))
    row = frame.iloc[-1]
    assert row.scan_unique_ports == len(set(ports))
    assert row.scan_sequential_score == sequential
    assert row.scan_randomized_score == randomized
    if len(set(ports)) > 1:
        assert frame.iloc[0].scan_unique_ports == 1
        assert frame.iloc[0].scan_sequential_score == 0


def test_session_timeout_and_ack_not_retransmission(tmp_path):
    packets = [Ether()/IP(src='10.0.0.1', dst='10.0.0.2')/TCP(sport=12,dport=80, seq=1,flags='A') for _ in range(3)]
    frame = pcap_to_dataframe(capture(tmp_path, packets), session_timeout=.5)
    assert len(frame) == 3
    assert frame.retransmission_count.sum() == 0
    with pytest.raises(ValueError, match='positive'):
        pcap_to_dataframe(tmp_path/'unused', session_timeout=0)


def test_resegmented_retransmission_and_sequence_wrap():
    flow = _new_flow(0)
    _add_sequence(flow, 100, 100)
    _add_sequence(flow, 150, 100)
    _add_sequence(flow, 250, 10)
    assert flow['retransmissions'] == 1
    wrapped = _new_flow(0)
    _add_sequence(wrapped, 2**32-5, 10)
    _add_sequence(wrapped, 0, 5)
    assert wrapped['retransmissions'] == 1


def test_named_taxonomy_and_unknowns():
    assert len(STAGE_NAMES) == 7
    cases = {'BENIGN':0, 'PORTSCAN':1, 'SSH-Bruteforce':2, 'Lateral Movement':3, 'BOT':4,
             'Command & Control':4, 'Exfiltration':5, 'DoS':6, 'Infiltration':6,
             'never-seen-attack':6, 'Reconnaissance and Exfiltration':6}
    for label, expected in cases.items():
        assert classify_stage(label) == expected
        assert UnifiedAdapter._stage(label) == expected
    mapping = yaml.safe_load((Path(__file__).resolve().parents[1]/'knowledge/stage_mapping.yaml').read_text(encoding='utf-8-sig'))
    for label, expected in mapping['label_to_stage'].items():
        assert classify_stage(label) == expected, label


def test_adapter_preserves_packet_fields_and_missingness(tmp_path):
    packet = Ether()/IP(src='10.0.0.1', dst='10.0.0.2')/UDP(sport=1,dport=53)/Raw(b'abc')
    frame = pcap_to_dataframe(capture(tmp_path, [packet]), label='BENIGN')
    converted = UnifiedAdapter('PCAP')._convert_df(frame)
    np.testing.assert_allclose(converted[list(PACKET_FEATURES)], frame[list(PACKET_FEATURES)])
    assert converted.bytes_fwd.iloc[0] == frame.bytes_fwd.iloc[0]
    plain = UnifiedAdapter('CIC-IDS2018')._convert_df(pd.DataFrame({'Source IP':['1'], 'Destination IP':['2'], 'Label':['BENIGN']}))
    assert plain.packet_features_available.iloc[0] == 0
    assert plain.attack_stage.iloc[0] == 0


def test_adapter_preserves_audited_stage_and_label_verification():
    row = {
        'timestamp': '2018-03-01T20:00:00Z',
        'src': '172.31.69.13',
        'dst': '162.125.18.133',
        'label': 'Infiltration - Dropbox Download',
        'stage': 2,
        'label_verified': True,
        'label_refinement_verified': False,
        'corrected_refinement_status': 'explicit-test-status',
    }
    row.update({name: 1.0 for name in PACKET_FEATURES})

    converted = UnifiedAdapter('CIC-IDS2018')._convert_df(pd.DataFrame([row]))

    assert converted.attack_stage.tolist() == [2]
    assert converted.label_verified.tolist() == [True]
    assert converted.label_refinement_verified.tolist() == [False]
    assert converted.corrected_refinement_status.tolist() == ['explicit-test-status']


def test_adapter_cannot_certify_synthesized_packet_values():
    row = {'Source IP': '1', 'Destination IP': '2', 'Label': 'BENIGN'}
    row.update({name: 1.0 for name in PACKET_FEATURES})
    row['ttl_mean'] = float('nan')
    row['packet_features_available'] = 1

    converted = UnifiedAdapter('CIC-IDS2018')._convert_df(pd.DataFrame([row]))

    assert converted.ttl_mean.tolist() == [0.0]
    assert converted.packet_features_available.tolist() == [0.0]
