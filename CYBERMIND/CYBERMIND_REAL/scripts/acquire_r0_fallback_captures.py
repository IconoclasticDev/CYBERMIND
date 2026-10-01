"""Freeze and acquire the reviewer-authorized R0 capture members.

Planning reads only already-saved archive directories. Acquisition downloads
exact ZIP members with resumable ranges, then verifies ZIP CRC, size and SHA256
before atomically publishing each PCAP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import time
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'examples/real_data_validation/r0/capture_scope_frozen.json'

SELECTED = {
    '2018-03-01': {
        'directory': 'examples/real_data_validation/r0/archive_2018-03-01.json',
        'members': [
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.13 part1',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.13 part2',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.13 part3',
        ],
        'scope_reason': 'All archive parts for the documented March 1 infiltration victim 172.31.69.13.',
    },
    '2018-03-02': {
        'directory': 'examples/real_data_validation/r0/archive_2018-03-02.json',
        'members': [
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.23',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.17',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.14',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.12',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.10',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.8',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.6',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.26',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.26a',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.29',
            'pcap/capEC2AMAZ-O4EL3NG-172.31.69.30',
        ],
        'scope_reason': 'All archive captures matching the ten bot victims in CIC Table 2; both files retained for 172.31.69.26.',
    },
}


def safe_name(member: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '_', member.removeprefix('pcap/')) + '.pcap'


def freeze_plan() -> dict:
    if PLAN.exists():
        raise FileExistsError(f'Frozen scope already exists: {PLAN}')
    records = []
    for date, selection in SELECTED.items():
        directory_path = ROOT / selection['directory']
        directory = json.loads(directory_path.read_text(encoding='utf-8'))
        by_name = {entry['name']: entry for entry in directory['entries']}
        if set(selection['members']) - set(by_name):
            raise ValueError(f'Missing selected members for {date}: {set(selection["members"]) - set(by_name)}')
        for member_name in selection['members']:
            member = by_name[member_name]
            if member['compression'] != 8 or not member['bytes']:
                raise ValueError(f'Unsupported selected member: {member}')
            records.append({
                'date': date,
                'archive_url': directory['url'],
                'archive_bytes': directory['archive_bytes'],
                'archive_directory_evidence': selection['directory'],
                'scope_reason': selection['scope_reason'],
                'member': member,
                'target': f'data/raw/CIC-IDS-2018/real_chunk/{date}/{safe_name(member_name)}',
            })
    result = {
        'status': 'frozen_before_acquisition',
        'frozen_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'selected_dates': ['2018-02-14', '2018-03-01', '2018-03-02'],
        'feb14_input': 'data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.complete_records.reviewed_2026-09-16.pcap',
        'feb14_evidence': 'examples/real_data_validation/r0/feb14_derivative.json',
        'additional_members': records,
        'additional_compressed_bytes': sum(r['member']['compressed_bytes'] for r in records),
        'additional_uncompressed_bytes': sum(r['member']['bytes'] for r in records),
        'labels_applied': False,
        'scope_note': 'Attack-relevant complete victim captures, not complete daily host populations.',
        'lateral_movement_transition_included': False,
    }
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    with PLAN.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return result


def member_data_start(record: dict) -> int:
    member, url = record['member'], record['archive_url']
    offset = member['offset']
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-{offset + 29}'})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 206:
            raise ValueError('Expected HTTP range response for local ZIP header')
        header = response.read(31)
    if len(header) != 30 or header[:4] != b'PK\x03\x04':
        raise ValueError('Invalid ZIP member header')
    fields = struct.unpack('<4s5H3I2H', header)
    if fields[2] & 1 or fields[3] != 8:
        raise ValueError('Unsupported encrypted or non-deflate ZIP member')
    return offset + 30 + fields[-2] + fields[-1]


def acquire(record: dict) -> dict:
    member = record['member']
    target = ROOT / record['target']
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence = target.with_suffix('.acquisition.json')
    if target.exists() or evidence.exists():
        raise FileExistsError(f'Preserve existing acquisition/evidence: {target}')
    compressed = target.with_suffix('.deflate.partial')
    start = member_data_start(record)
    total = member['compressed_bytes']
    begin = time.monotonic()
    for attempt in range(8):
        have = compressed.stat().st_size if compressed.exists() else 0
        if have == total:
            break
        if have > total:
            raise ValueError('Partial compressed file exceeds expected size')
        request = urllib.request.Request(
            record['archive_url'], headers={'Range': f'bytes={start + have}-{start + total - 1}'})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 206:
                    raise ValueError('Server ignored member range')
                expected = f'bytes {start + have}-{start + total - 1}/{record["archive_bytes"]}'
                if response.headers.get('Content-Range') != expected:
                    raise ValueError('Unexpected member content range')
                with compressed.open('ab') as stream:
                    while chunk := response.read(4 * 1024 * 1024):
                        stream.write(chunk)
                        have += len(chunk)
                        print(f'{record["date"]} {member["name"]}: {have}/{total}', flush=True)
        except (OSError, TimeoutError) as error:
            print(f'Retry {attempt + 1}: {error}', flush=True)
    if not compressed.exists() or compressed.stat().st_size != total:
        raise ValueError('Incomplete member acquisition')

    temporary = target.with_suffix('.pcap.partial')
    decoder = zlib.decompressobj(-15)
    checksum = 0
    count = 0
    sha = hashlib.sha256()
    with compressed.open('rb') as source, temporary.open('xb') as destination:
        while chunk := source.read(1024 * 1024):
            decoded = decoder.decompress(chunk)
            destination.write(decoded)
            sha.update(decoded)
            checksum = zlib.crc32(decoded, checksum)
            count += len(decoded)
        decoded = decoder.flush()
        destination.write(decoded)
        sha.update(decoded)
        checksum = zlib.crc32(decoded, checksum)
        count += len(decoded)
    if (not decoder.eof or decoder.unused_data or count != member['bytes']
            or f'{checksum:08x}' != member['crc32']):
        raise ValueError('Complete member CRC/length verification failed')
    temporary.replace(target)
    result = {
        **record,
        'status': 'complete_member_verified',
        'target_bytes': count,
        'target_sha256': sha.hexdigest(),
        'target_crc32': f'{checksum:08x}',
        'seconds': time.monotonic() - begin,
        'labels_applied': False,
    }
    with evidence.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return result


def verified_existing(record: dict) -> dict | None:
    """Return existing evidence only after re-verifying the published PCAP."""
    target = ROOT / record['target']
    evidence_path = target.with_suffix('.acquisition.json')
    if not target.exists() and not evidence_path.exists():
        return None
    if not target.exists() or not evidence_path.exists():
        raise FileExistsError(f'Incomplete existing acquisition/evidence pair: {target}')
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    digest = hashlib.sha256()
    with target.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if (evidence.get('status') != 'complete_member_verified'
            or evidence.get('target') != record['target']
            or evidence.get('target_bytes') != record['member']['bytes']
            or target.stat().st_size != record['member']['bytes']
            or evidence.get('target_crc32') != record['member']['crc32']
            or evidence.get('target_sha256') != digest.hexdigest()):
        raise ValueError(f'Existing acquisition failed re-verification: {target}')
    print(f'SKIP re-verified complete acquisition: {target}', flush=True)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--skip-verified-complete', action='store_true')
    args = parser.parse_args()
    if args.freeze == args.download:
        parser.error('choose exactly one of --freeze or --download')
    if args.freeze:
        print(json.dumps(freeze_plan(), indent=2))
        return
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    if plan['status'] != 'frozen_before_acquisition':
        raise ValueError('Capture scope is not the expected frozen plan')
    results = []
    for record in plan['additional_members']:
        if args.skip_verified_complete:
            existing = verified_existing(record)
            if existing is not None:
                results.append(existing)
                continue
        results.append(acquire(record))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
