import csv
import json
from pathlib import Path

import pytest
from scapy.all import Ether, IP, TCP, Raw, wrpcap

from cybermind.data.pcap_extract import PACKET_FEATURES
from cybermind.data.real_chunk_export import export_capture, PROVENANCE_LABEL
from cybermind.data.cic_day import packets as parsed_packets


def capture(path):
    packets = []
    for index, timestamp in enumerate((1.0, 1.5, 400.0)):
        packet = Ether()/IP(src='10.0.0.1', dst='10.0.0.2', ttl=60+index, flags='DF')/TCP(
            sport=12345, dport=443, seq=100+index*4, flags='PA', window=1000+index)/Raw(b'test')
        packet.time = timestamp
        packets.append(packet)
    wrpcap(str(path), packets)


def test_unlabeled_export_is_atomic_and_carries_exact_provenance(tmp_path):
    source = tmp_path/'source.pcap'; capture(source)
    output = tmp_path/'flows.csv'; report = tmp_path/'report.json'
    result = export_capture(source, output, report, capture_date='2018-01-01',
                            capture_member='fixture', session_timeout=300)
    assert result['status'] == 'complete_unlabeled_fallback_export'
    assert not output.with_name(output.name+'.partial').exists()
    rows = list(csv.DictReader(output.open(encoding='utf-8')))
    assert len(rows) == 2
    assert not {'label', 'stage', 'attack_stage', 'infiltration'} & set(rows[0])
    assert {'src', 'dst', 'src_port', 'dst_port', 'protocol'} <= set(rows[0])
    assert set(PACKET_FEATURES) <= set(rows[0])
    assert all(row['flow_feature_source'] == PROVENANCE_LABEL for row in rows)
    assert all(row['labels_applied'] == 'False' for row in rows)
    assert json.loads(report.read_text())['output_sha256'] == result['output_sha256']


def test_existing_paths_are_never_overwritten(tmp_path):
    source = tmp_path/'source.pcap'; capture(source)
    output = tmp_path/'flows.csv'; output.write_text('preserve', encoding='utf-8')
    with pytest.raises(FileExistsError):
        export_capture(source, output, tmp_path/'report.json', capture_date='x', capture_member='x')
    assert output.read_text(encoding='utf-8') == 'preserve'


def test_complete_tcp_offload_record_with_zero_ipv4_total_is_counted(tmp_path):
    source = tmp_path/'offload.pcap'
    packet = Ether()/IP(src='10.0.0.1', dst='10.0.0.2')/TCP(sport=12345, dport=443)/Raw(b'x'*2000)
    packet.time = 1.0
    wrpcap(str(source), [packet])
    raw = bytearray(source.read_bytes())
    # classic PCAP global header + record header + Ethernet header + IPv4 total-length field
    raw[24 + 16 + 14 + 2:24 + 16 + 14 + 4] = b'\x00\x00'
    source.write_bytes(raw)
    parsed = list(parsed_packets(source))
    assert len(parsed) == 1
    assert parsed[0]['ipv4_total_length_zero_offload'] is True
    output = tmp_path/'flows.csv'; report = tmp_path/'report.json'
    result = export_capture(source, output, report, capture_date='2018-03-01', capture_member='offload')
    assert result['counts']['ipv4_total_length_zero_offload_records'] == 1
