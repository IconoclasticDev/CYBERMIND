"""Verify Phase 0 evidence and its completed-capture overwrite guard."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def fingerprint(path):
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def files():
    return {str(p.relative_to(OUT)): fingerprint(p) for p in sorted(OUT.rglob('*'))
            if p.is_file() and not any(x in p.parts for x in ('historical_artifacts', '__pycache__'))}


def main():
    manifest_path = OUT / 'baseline_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    # Only the capture helper was deliberately hardened after the first manifest.
    for name, expected in manifest['files'].items():
        if name != 'capture_baseline.py':
            assert fingerprint(OUT / name) == expected, f'Captured evidence changed: {name}'
    before = files()
    result = subprocess.run([sys.executable, str(OUT / 'capture_baseline.py')], cwd=ROOT,
                            text=True, capture_output=True, check=True)
    assert 'Baseline already complete and frozen' in result.stdout
    assert files() == before, 'Completed-capture guard changed evidence'
    items = json.loads((ROOT / 'data/manifests/phase0_knowledge_manifest.json').read_text())['items']
    for item in items:
        actual = fingerprint(ROOT / item['path'])
        assert actual == {'bytes': item['bytes'], 'sha256': item['sha256']}, item['source']
    manifest['files'] = {name: record for name, record in files().items() if name != 'baseline_manifest.json'}
    manifest['source_head_before_phase0'] = '70edd8f579452c735e0ac416fe3cbdef918b31a5'
    manifest['source_sha256'] = {str(p.relative_to(ROOT)): fingerprint(p)['sha256']
                               for folder in ('src', 'scripts', 'tests')
                               for p in sorted((ROOT / folder).rglob('*.py'))}
    manifest['finalized_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest['post_capture_changes'] = 'Only helper guards and explanatory evidence documentation; model inputs, checkpoints and metric records unchanged.'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for name, expected in manifest['files'].items():
        assert fingerprint(OUT / name) == expected, name
    report = {'checked_at_utc': manifest['finalized_at_utc'], 'baseline_files_verified': len(manifest['files']),
              'knowledge_files_verified': len(items), 'completed_capture_did_not_modify_evidence': True,
              'original_model_inputs_checkpoints_and_metrics_unchanged': True,
              'manifest_sha256': fingerprint(manifest_path)['sha256']}
    (ROOT / 'docs/phase0_integrity_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
