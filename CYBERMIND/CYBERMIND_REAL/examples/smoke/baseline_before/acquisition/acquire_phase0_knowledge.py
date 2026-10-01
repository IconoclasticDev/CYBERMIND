"""Acquire the three lightweight Phase 0 sources without touching legacy provenance."""
import datetime
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[4]
SOURCES = [
    ('ATT&CK', 'https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json', 'enterprise-attack.json'),
    ('CAPEC', 'https://capec.mitre.org/data/archive/capec_latest.zip', 'capec_latest.zip'),
    ('NVD', 'https://services.nvd.nist.gov/rest/json/cves/2.0?startIndex=0&resultsPerPage=2000', 'nvd_cves_page_0.json'),
]

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def validate(source, path):
    if source == 'CAPEC':
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC verification failed')
            records = []
            for name in archive.namelist():
                if name.lower().endswith('.xml'):
                    root = ET.fromstring(archive.read(name))
                    records.append({'member': name, 'root': root.tag, 'version': root.attrib.get('Version'), 'attack_pattern_count': sum(e.tag.rsplit('}', 1)[-1] == 'Attack_Pattern' for e in root.iter())})
            if not records or not any(r['attack_pattern_count'] for r in records):
                raise ValueError('No CAPEC attack patterns in ZIP XML')
            return {'zip_crc': 'passed', 'xml_parse': 'passed', 'catalogs': records}
    obj = json.loads(path.read_text(encoding='utf-8'))
    if source == 'ATT&CK':
        if obj.get('type') != 'bundle' or not obj.get('objects'):
            raise ValueError('Not a nonempty STIX bundle')
        collections = [e for e in obj['objects'] if e.get('type') == 'x-mitre-collection']
        return {'json_parse': 'passed', 'stix_bundle': 'passed', 'object_count': len(obj['objects']), 'attack_pattern_count': sum(e.get('type') == 'attack-pattern' for e in obj['objects']), 'collection_versions': [e.get('x_mitre_version') for e in collections]}
    if obj.get('startIndex') != 0 or not obj.get('vulnerabilities'):
        raise ValueError('Expected nonempty NVD page zero')
    return {'json_parse': 'passed', 'record_count': len(obj['vulnerabilities']), 'version': obj.get('version'), 'start_index': obj['startIndex'], 'total_results_on_server': obj.get('totalResults'), 'server_timestamp': obj.get('timestamp'), 'scope': 'LIMITED SNAPSHOT: first page, at most 2000 CVEs; NOT the complete NVD database'}

def main():
    manifest_path = ROOT / 'data/manifests/phase0_knowledge_manifest.json'
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'items': []}
    prior_items = {item['source']: item for item in prior['items']}
    results = []
    for source, url, name in SOURCES:
        target = ROOT / 'knowledge/raw' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        entry = {'source': source, 'url': url, 'path': target.relative_to(ROOT).as_posix()}
        try:
            if target.exists():
                validation = validate(source, target)
                entry.update(prior_items.get(source, {}))
                entry['acquisition_action'] = 'reused_existing_valid_file'
            else:
                staged = target.with_suffix(target.suffix + '.part')
                with urlopen(Request(url, headers={'User-Agent': 'CYBERMIND-research-downloader/1.0'}), timeout=180) as response, staged.open('wb') as out:
                    entry.update({'download_started_at_utc': now(), 'resolved_url': response.geturl(), 'http_last_modified': response.headers.get('Last-Modified'), 'http_etag': response.headers.get('ETag')})
                    for chunk in iter(lambda: response.read(1024 * 1024), b''):
                        out.write(chunk)
                validation = validate(source, staged)
                staged.replace(target)
                entry.update({'download_completed_at_utc': now(), 'acquisition_action': 'downloaded_and_atomically_committed'})
            entry.update({'status': 'verified', 'verified_at_utc': now(), 'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'validation': validation, 'checksum_note': 'Locally computed SHA256; no independently published checksum compared.'})
        except Exception as exc:
            entry.update({'status': 'failed', 'error': str(exc), 'attempted_at_utc': now()})
        results.append(entry)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        staged_manifest = manifest_path.with_suffix('.json.part')
        staged_manifest.write_text(json.dumps({'generated_at_utc': now(), 'scope': 'Phase 0 lightweight knowledge only; heavy datasets deferred to Phase 5', 'items': results}, indent=2), encoding='utf-8')
        staged_manifest.replace(manifest_path)
        print(json.dumps(entry), flush=True)
    if any(item['status'] != 'verified' for item in results):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
