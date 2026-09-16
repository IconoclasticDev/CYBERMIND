"""Atomic, label-free fallback flow export for reviewed real-chunk PCAPs."""
from __future__ import annotations

import csv
import hashlib
import heapq
import json
from pathlib import Path
import time

import numpy as np

from .cic_day import packets
from .pcap_extract import _add_sequence, _new_flow, _row, _scan_features, PACKET_FEATURES

PROVENANCE_LABEL = (
    'flow_feature_source: CYBERMIND custom directional packet exporter; 40-column '
    "schema; satisfies the project's 20-field packet-feature contract when verified, "
    'but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter '
    'traffic-statistic columns. No CICFlowMeter feature parity is claimed.'
)
SEMANTICS = 'directional IPv4 sessions; 300-second inactivity timeout; no biflow merge'


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def export_capture(source, output, report_path, *, capture_date, capture_member,
                   expected_sha256=None, session_timeout=300.0):
    source, output, report_path = Path(source), Path(output), Path(report_path)
    partial = output.with_name(output.name + '.partial')
    report_partial = report_path.with_name(report_path.name + '.partial')
    if any(path.exists() for path in (output, partial, report_path, report_partial)):
        raise FileExistsError('Preserve existing final, partial, and report paths')
    if session_timeout <= 0:
        raise ValueError('session_timeout must be positive')
    source_hash = sha256(source)
    if expected_sha256 and source_hash.lower() != expected_sha256.lower():
        raise ValueError('Source SHA256 differs from acquisition evidence')
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    flows, expiry_heap, scans = {}, [], {}
    counts = {'capture_records': 0, 'ipv4_packets_processed': 0,
              'non_ipv4': 0, 'fragmented_ipv4': 0,
              'ipv4_total_length_zero_offload_records': 0, 'rows': 0}
    first = last = None
    writer = stream = None
    started = time.monotonic()

    def publish(key, flow):
        nonlocal writer, stream
        row = _row(key, flow, None)
        row['timestamp'] = row['timestamp'].isoformat() + 'Z'
        row['session_start'] = row['session_start'].isoformat() + 'Z'
        row.update(
            capture_date=capture_date,
            capture_member=capture_member,
            source_pcap_sha256=source_hash,
            labels_applied=False,
            flow_semantics=SEMANTICS,
            flow_feature_source=PROVENANCE_LABEL,
        )
        if writer is None:
            stream = partial.open('x', encoding='utf-8', newline='')
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
        writer.writerow(row)
        counts['rows'] += 1

    def expire(now):
        boundary = now - session_timeout
        while expiry_heap and expiry_heap[0][0] < boundary:
            recorded_last, key = heapq.heappop(expiry_heap)
            flow = flows.get(key)
            if flow is not None and flow['last'] == recorded_last:
                publish(key, flows.pop(key))

    try:
        for packet in packets(source):
            timestamp = packet['time']
            first = timestamp if first is None else first
            last = timestamp
            counts['capture_records'] += 1
            expire(timestamp)
            if 'skip' in packet:
                counts[packet['skip']] = counts.get(packet['skip'], 0) + 1
                continue
            counts['ipv4_packets_processed'] += 1
            if packet.get('ipv4_total_length_zero_offload'):
                counts['ipv4_total_length_zero_offload_records'] += 1
            key = (packet['src'], packet['dst'], packet['proto'], packet['sport'], packet['dport'])
            if key in flows and timestamp - flows[key]['last'] > session_timeout:
                publish(key, flows.pop(key))
            pair = (packet['src'], packet['dst'], packet['proto'])
            scan = scans.get(pair)
            if scan is None or timestamp - scan['last'] > session_timeout:
                scan = scans[pair] = {'last': timestamp, 'ports': []}
            scan['last'] = timestamp
            if packet['proto'] in (6, 17) and packet['dport'] not in scan['ports']:
                scan['ports'].append(packet['dport'])

            flow = flows.setdefault(key, _new_flow(timestamp))
            if flow['packets']:
                flow['iats'].append(timestamp - flow['last'])
            flow['last'] = timestamp
            flow['packets'] += 1
            flow['bytes'] += packet['captured_bytes']
            flow['ttls'].append(packet['ttl'])
            flow['df'] += packet['df']
            flow['payloads'].append(packet['payload'])
            flow['scan'] = _scan_features(scan['ports'])
            if packet['proto'] == 6:
                flow['windows'].append(packet['window'])
                sequence_length = packet['payload'] + bool(packet['tcpflags'] & 2) + bool(packet['tcpflags'] & 1)
                _add_sequence(flow, packet['seq'], sequence_length)
            heapq.heappush(expiry_heap, (flow['last'], key))
            if counts['capture_records'] % 500_000 == 0:
                print(json.dumps(counts), flush=True)
        for key, flow in sorted(flows.items(), key=lambda item: item[1]['last']):
            publish(key, flow)
        if writer is None:
            raise ValueError('Capture produced no exported IPv4 flows')
        stream.flush()
        stream.close()
        stream = None
        output_hash = sha256(partial)
        report = {
            'status': 'complete_unlabeled_fallback_export',
            'source': str(source), 'source_bytes': source.stat().st_size,
            'source_sha256': source_hash, 'output': str(output),
            'output_sha256': output_hash, 'capture_date': capture_date,
            'capture_member': capture_member, 'labels_applied': False,
            'session_timeout_seconds': session_timeout, 'counts': counts,
            'first_packet_epoch': first, 'last_packet_epoch': last,
            'flow_feature_source': PROVENANCE_LABEL,
            'flow_semantics': SEMANTICS,
            'packet_feature_fields': list(PACKET_FEATURES),
            'packet_feature_field_count': len(PACKET_FEATURES),
            'cicflowmeter_feature_parity_claimed': False,
            'approximately_missing_cic_traffic_statistics': 67,
            'non_ipv4_and_fragment_policy': 'excluded and counted; no reassembly or invented transport tuple',
            'offload_record_policy': (
                'IPv4 total-length zero is accepted only for complete TCP capture records '
                '(captured length equals wire length) with a full TCP header; total length '
                'is derived from captured IP bytes, records are counted, and source bytes remain unchanged.'
            ),
            'seconds': time.monotonic() - started,
        }
        with report_partial.open('x', encoding='utf-8') as report_stream:
            json.dump(report, report_stream, indent=2)
        partial.replace(output)
        report_partial.replace(report_path)
        return report
    except Exception as error:
        if stream is not None:
            stream.close()
        failure = {
            'status': 'failed_unlabeled_fallback_export',
            'error_type': type(error).__name__, 'error': str(error),
            'source': str(source), 'output': str(output),
            'partial_output': str(partial) if partial.exists() else None,
            'counts': counts, 'labels_applied': False,
            'flow_feature_source': PROVENANCE_LABEL,
        }
        if not report_path.exists() and not report_partial.exists():
            with report_path.open('x', encoding='utf-8') as failure_stream:
                json.dump(failure, failure_stream, indent=2)
        raise
