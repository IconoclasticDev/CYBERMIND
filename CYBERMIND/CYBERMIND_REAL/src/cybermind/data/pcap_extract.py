"""Read-only PCAP extraction: directional sessions and packet statistics.

Scan scores describe port order, never an attack label or an ingestion gate.
All variances are population variances. TCP windows are raw advertised values.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from cybermind.data.stages import classify_stage

PACKET_FEATURES = (
    'ttl_mean', 'ttl_variance', 'tcp_window_mean', 'tcp_window_variance',
    'ip_df_ratio', 'ip_mf_ratio', 'ip_fragment_ratio', 'payload_size_mean',
    'payload_size_variance', 'payload_size_min', 'payload_size_max',
    'payload_size_p25', 'payload_size_p50', 'payload_size_p75',
    'scan_unique_ports', 'scan_sequential_score', 'scan_randomized_score',
    'retransmission_count', 'retransmission_ratio', 'packet_features_available',
)


def _scan_features(ports, minimum_ports=4):
    """Irregular order is a randomized-scan signature, not proof of randomness."""
    unique = list(dict.fromkeys(ports))
    if len(unique) < minimum_ports:
        return float(len(unique)), 0.0, 0.0
    sequential = float(np.mean(np.abs(np.diff(unique)) == 1))
    return float(len(unique)), sequential, 1.0 - sequential


def _new_flow(t):
    return dict(first=t, last=t, packets=0, bytes=0, iats=[], ttls=[], windows=[],
                payloads=[], df=0, mf=0, fragments=0, retransmissions=0,
                sequence_ranges=[], scan=(0.0, 0.0, 0.0))


def _add_sequence(flow, sequence, length):
    """Count overlapping sequence-space segments, including SYN/FIN retries.

    Pure ACKs are excluded. Interval merging handles resegmentation and wrap.
    """
    if length <= 0:
        return
    modulus = 1 << 32
    end = sequence + length
    spans = [(sequence, min(end, modulus))]
    if end > modulus:
        spans.append((0, end - modulus))
    old = flow['sequence_ranges']
    if any(a < d and c < b for a, b in spans for c, d in old):
        flow['retransmissions'] += 1
    merged = []
    for start, stop in sorted(old + spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(stop, merged[-1][1]))
        else:
            merged.append((start, stop))
    flow['sequence_ranges'] = merged


def _row(key, f, label=None):
    src, dst, proto, sport, dport = key
    duration = max(0.0, f['last'] - f['first'])
    payload = np.asarray(f['payloads'], dtype=np.float64)
    windows = np.asarray(f['windows'], dtype=np.float64)
    count = f['packets']
    if payload.size == 1:
        payload_mean = payload_min = payload_max = q25 = q50 = q75 = float(payload[0])
        payload_variance = 0.0
    else:
        payload_mean, payload_variance = float(payload.mean()), float(payload.var())
        payload_min, payload_max = float(payload.min()), float(payload.max())
        q25, q50, q75 = (float(value) for value in np.quantile(payload, (.25, .5, .75)))
    # Aggregate values are available only after the last included packet.
    # Dating them at session start leaks later telemetry into earlier windows.
    row = dict(timestamp=pd.to_datetime(f['last'], unit='s'),
                session_start=pd.to_datetime(f['first'], unit='s'), src=src, dst=dst,
                protocol=float(proto), src_port=float(sport), dst_port=float(dport),
                duration=duration, bytes_fwd=float(f['bytes']), bytes_bwd=0.0,
                packets_fwd=float(count), packets_bwd=0.0,
                mean_fwd_iat=float(np.mean(f['iats'])) if f['iats'] else 0.0,
                mean_bwd_iat=0.0, flow_bytes_s=f['bytes']/max(duration, 1e-6),
                flow_packets_s=count/max(duration, 1e-6),
                ttl_mean=float(np.mean(f['ttls'])), ttl_variance=float(np.var(f['ttls'])),
                tcp_window_mean=float(windows.mean()) if windows.size else 0.0,
                tcp_window_variance=float(windows.var()) if windows.size else 0.0,
                ip_df_ratio=f['df']/count, ip_mf_ratio=f['mf']/count,
                ip_fragment_ratio=f['fragments']/count,
                payload_size_mean=payload_mean, payload_size_variance=payload_variance,
                payload_size_min=payload_min, payload_size_max=payload_max,
                payload_size_p25=q25, payload_size_p50=q50, payload_size_p75=q75,
                scan_unique_ports=f['scan'][0], scan_sequential_score=f['scan'][1],
                scan_randomized_score=f['scan'][2], retransmission_count=float(f['retransmissions']),
                retransmission_ratio=f['retransmissions']/count, packet_features_available=1.0)
    if label is not None:
        stage = classify_stage(label)
        row.update(label=label, infiltration=float(stage != 0), stage=stage, attack_stage=stage)
    return row


def pcap_to_dataframe(path: str | Path, label='PCAP_EVENT', session_timeout=300.0):
    """Aggregate IPv4 packets; split flow/host-pair state after inactivity.

    Captures must be chronologically ordered. Missing IPv6 support is explicit:
    non-IPv4 frames are skipped, rather than inventing TTL/fragment statistics.
    """
    if session_timeout <= 0:
        raise ValueError('session_timeout must be positive')
    try:
        from scapy.all import IP, TCP, UDP, PcapReader
    except ImportError as error:
        raise RuntimeError('scapy is required for PCAP extraction') from error
    flows, scans, rows = {}, {}, []
    previous_time = None
    with PcapReader(str(path)) as reader:
        for packet in reader:
            if not packet.haslayer(IP):
                continue
            ip = packet[IP]
            src, dst, proto = str(ip.src), str(ip.dst), int(ip.proto)
            t = float(packet.time)
            if previous_time is not None and t < previous_time:
                raise ValueError('PCAP packets must be in chronological order')
            previous_time = t
            transport = packet[TCP] if packet.haslayer(TCP) else packet[UDP] if packet.haslayer(UDP) else None
            sport, dport = (int(transport.sport), int(transport.dport)) if transport is not None else (0, 0)
            key = (src, dst, proto, sport, dport)
            if key in flows and t - flows[key]['last'] > session_timeout:
                rows.append(_row(key, flows.pop(key), label))
            flow = flows.setdefault(key, _new_flow(t))
            if flow['packets']:
                flow['iats'].append(t - flow['last'])
            flow['last'] = t
            flow['packets'] += 1
            flow['bytes'] += len(packet)
            flow['ttls'].append(int(ip.ttl))
            flow['df'] += bool(int(ip.flags) & 2)
            flow['mf'] += bool(int(ip.flags) & 1)
            flow['fragments'] += bool(int(ip.flags) & 1 or int(ip.frag) > 0)
            payload_length = len(bytes(transport.payload if transport is not None else ip.payload))
            flow['payloads'].append(payload_length)
            if packet.haslayer(TCP):
                tcp = packet[TCP]
                flow['windows'].append(int(tcp.window))
                length = payload_length + bool(int(tcp.flags) & 2) + bool(int(tcp.flags) & 1)
                _add_sequence(flow, int(tcp.seq), length)
            pair = (src, dst, proto)
            if pair not in scans or t - scans[pair]['last'] > session_timeout:
                scans[pair] = dict(last=t, ports=[])
            scan = scans[pair]
            scan['last'] = t
            if transport is not None and dport not in scan['ports']:
                scan['ports'].append(dport)
            # Snapshot only prior/current observations, never future ports.
            flow['scan'] = _scan_features(scan['ports'])
    rows.extend(_row(key, flow, label) for key, flow in flows.items())
    if not rows:
        return pd.DataFrame(columns=('timestamp', 'src', 'dst', 'label', 'stage', 'attack_stage') + PACKET_FEATURES)
    return pd.DataFrame(rows).sort_values('timestamp', kind='stable').reset_index(drop=True)
