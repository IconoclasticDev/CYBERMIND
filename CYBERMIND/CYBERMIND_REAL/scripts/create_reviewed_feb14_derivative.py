"""Apply only the exact PCAP-prefix derivative approved on 2026-09-16."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.pcap'
DEST = SOURCE.with_name('UCAP172.31.69.25.complete_records.reviewed_2026-09-16.pcap')
REPORT = ROOT / 'examples/real_data_validation/r0/feb14_derivative.json'
SOURCE_SHA = '008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc'
CUTOFF = 852795085


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    partial = DEST.with_name(DEST.name + '.partial')
    if any(p.exists() for p in (DEST, partial, REPORT)):
        raise FileExistsError('Preserve existing derivative and evidence')
    if SOURCE.stat().st_size != 852795392 or digest(SOURCE) != SOURCE_SHA:
        raise ValueError('Source does not match the approved capture')
    count = 0
    with SOURCE.open('rb') as src:
        header = src.read(24)
        if header[:4] != b'\xd4\xc3\xb2\xa1':
            raise ValueError('Unexpected approved source format')
        while src.tell() < CUTOFF:
            record = src.read(16)
            if len(record) != 16:
                raise ValueError('Incomplete record before approved cutoff')
            _, _, size, _ = struct.unpack('<4I', record)
            if src.tell() + size > CUTOFF:
                raise ValueError('Cutoff splits a supposedly complete record')
            src.seek(size, 1)
            count += 1
        if src.tell() != CUTOFF or count != 4718327:
            raise ValueError('Record count or cutoff differs from approval')
        tail = src.read()
        if len(tail) != 307 or struct.unpack('<4I', tail[:16])[2] != 371:
            raise ValueError('Excluded record differs from approval')
        src.seek(0)
        prefix_sha = hashlib.sha256()
        remaining = CUTOFF
        with partial.open('xb') as dst:
            while remaining:
                block = src.read(min(4 * 1024 * 1024, remaining))
                if not block:
                    raise ValueError('Unexpected EOF copying approved prefix')
                dst.write(block)
                prefix_sha.update(block)
                remaining -= len(block)
    derivative_sha = digest(partial)
    source_after = digest(SOURCE)
    if derivative_sha != prefix_sha.hexdigest() or source_after != SOURCE_SHA:
        raise ValueError('Byte-copy or source-preservation check failed')
    partial.rename(DEST)
    result = {
        'status': 'approved_derivative_verified_not_flow_export',
        'authorization': 'docs/REAL_DATA_R0_REVIEWER_DECISION_2026_09_16.md',
        'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': SOURCE_SHA,
        'source_sha256_after': source_after, 'source_unchanged': True,
        'derivative': str(DEST.relative_to(ROOT)), 'derivative_sha256': derivative_sha,
        'derivative_bytes': CUTOFF, 'complete_packet_records': count,
        'identical_to_source_prefix': True,
        'excluded_record': {'offset': CUTOFF, 'declared_payload_bytes': 371,
                            'available_payload_bytes': 291, 'on_disk_bytes': 307,
                            'missing_payload_bytes': 80, 'tail_sha256': hashlib.sha256(tail).hexdigest()},
        'byte_synthesis': False, 'record_repair': False,
        'scope': 'One victim-host capture; truncated final record omitted by explicit reviewer approval',
        'r0_exit_criteria_met': False,
        'selected_dates': ['2018-02-14', '2018-03-01', '2018-03-02'],
        'coverage_disclosure': 'Real-chunk validation does not include a Lateral Movement transition. Kill-chain-diversity validation on real data covers the other represented stages only; it does not validate Lateral Movement.',
        'real_data_validation_status': 'not yet performed'
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
