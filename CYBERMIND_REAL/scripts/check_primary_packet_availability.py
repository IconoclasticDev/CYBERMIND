#!/usr/bin/env python3
"""Phase 4.4: bounded anonymous metadata checks, never download corpus objects."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/'
NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='examples/phase4/packet_availability')
    args=parser.parse_args();out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    records=[];requests=[]
    for label,prefix in [('original','Original Network Traffic and Log data/'),('processed','Processed Traffic Data for ML Algorithms/')]:
        url=ENDPOINT+'?'+urllib.parse.urlencode({'list-type':'2','prefix':prefix,'max-keys':'1000'})
        with urllib.request.urlopen(url,timeout=30) as response:
            payload=response.read(2_000_001)
            assert len(payload)<=2_000_000,'Metadata listing exceeds bounded inspection limit'
            requests.append({'method':'GET metadata listing','url':url,'status':response.status,'response_bytes':len(payload)})
        (out/f'{label}_listing.xml').write_bytes(payload)
        tree=ET.fromstring(payload)
        assert tree.findtext('s:IsTruncated',namespaces=NS)=='false','Listing incomplete; do not report whole-corpus sizes'
        for entry in tree.findall('s:Contents',NS):
            records.append(dict(key=entry.findtext('s:Key',namespaces=NS),bytes=int(entry.findtext('s:Size',namespaces=NS)),
                                etag=entry.findtext('s:ETag',namespaces=NS),group=label))
    pcaps=[r for r in records if r['key'].lower().endswith(('/pcap.zip','/pcap.rar'))]
    assert pcaps,'No public PCAP archives in authoritative listing'
    for item in pcaps:
        url=ENDPOINT+urllib.parse.quote(item['key'],safe='/')
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as response:
            assert int(response.headers['Content-Length'])==item['bytes']
            item['head_status']=response.status
            item['last_modified']=response.headers.get('Last-Modified')
            requests.append({'method':'HEAD','url':url,'status':response.status,'object_bytes':item['bytes'],'body_downloaded':False})
    raw=ROOT/'data/raw/CIC-IDS-2018'
    local=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size} for p in raw.rglob('*') if p.is_file()] if raw.exists() else []
    csvs=[r for r in records if r['group']=='processed' and r['key'].lower().endswith('.csv')]
    dates=lambda rows:sorted({re.search(r'\d{2}-\d{2}-\d{4}',r['key']).group() for r in rows})
    result=dict(checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        official_registry='https://registry.opendata.aws/cse-cic-ids2018/',
        official_description='https://www.unb.ca/cic/datasets/ids-2018.html',
        bucket='cse-cic-ids2018',region='ca-central-1',anonymous_access=True,
        remote_pcaps_available=True,pcap_archive_count=len(pcaps),pcap_archive_bytes=sum(r['bytes'] for r in pcaps),
        processed_csv_count=len(csvs),processed_csv_bytes=sum(r['bytes'] for r in csvs),
        pcap_dates=dates(pcaps),csv_dates=dates(csvs),all_csv_dates_have_pcap_archives=dates(pcaps)==dates(csvs),
        archive_formats=sorted({Path(r['key']).suffix for r in pcaps}),
        uncompressed_capture_bytes='not inspected',objects=records,pcap_archives=pcaps,requests=requests,
        local_primary_files=local,corpus_payload_downloaded=False,
        local_feature_complete_primary_corpus_ready=False,
        strict_requirement_retained=True,
        preparation_blockers=['Full captures/flow labels not acquired locally; acquisition remains Phase 5 on GB10.',
          'PCAPs must be extracted and reliably joined/labeled from authoritative scenario/endpoint/time ground truth before strict primary preparation.',
          'pcap_to_corpus.py assigns filename-derived labels and source PCAP; it is not a verified CIC-IDS2018 enrichment/label-join pipeline. Do not treat PCAP_EVENT as benign or real ground truth.'],
        listing_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*_listing.xml')})
    (out/'availability.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('objects','pcap_archives','requests','local_primary_files')}))


if __name__=='__main__':main()
