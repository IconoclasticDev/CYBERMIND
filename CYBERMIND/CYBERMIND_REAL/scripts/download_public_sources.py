#!/usr/bin/env python3
"""Download/prepare only what is publicly and programmatically accessible.
Large research datasets remain user-triggered because they may be tens/hundreds of GB or require a web form.
"""
from pathlib import Path
import argparse, json, subprocess, sys, urllib.request, zipfile, hashlib, time
ROOT=Path(__file__).resolve().parents[1]

SOURCES={
 'cic2018_s3':'s3://cse-cic-ids2018/',
 'attack_enterprise':'https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json',
 'capec_latest':'https://capec.mitre.org/data/archive/capec_latest.zip',
}

def sha256(path):
    h=hashlib.sha256();
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def download_url(url,out):
    out.parent.mkdir(parents=True,exist_ok=True); print('GET',url)
    with urllib.request.urlopen(url,timeout=120) as r, open(out,'wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',choices=sorted(SOURCES),action='append'); ap.add_argument('--cic-prefix',default='',help='Optional CIC2018 S3 prefix/date, e.g. "Processed Traffic Data for ML Algorithms/Friday-02-03-2018/"'); args=ap.parse_args()
    chosen=args.source or ['attack_enterprise','capec_latest']
    prov=[]
    for name in chosen:
        if name=='cic2018_s3':
            ROOT.joinpath('data/raw/CIC-IDS-2018').mkdir(parents=True,exist_ok=True)
            cmd=['aws','s3','sync','--no-sign-request',SOURCES[name],str(ROOT/'data/raw/CIC-IDS-2018')]
            if args.cic_prefix:
                cmd=['aws','s3','sync','--no-sign-request',SOURCES[name]+args.cic_prefix,str(ROOT/'data/raw/CIC-IDS-2018')]
            subprocess.run(cmd,check=True)
            prov.append({'source':name,'method':'aws s3 sync','uri':SOURCES[name]+args.cic_prefix})
        else:
            out=ROOT/'knowledge'/('enterprise-attack.json' if name=='attack_enterprise' else 'capec_latest.zip')
            try:
                download_url(SOURCES[name],out); prov.append({'source':name,'url':SOURCES[name],'sha256':sha256(out),'bytes':out.stat().st_size})
            except Exception as e:
                print('WARNING',name,e)
    (ROOT/'data/manifests'/'download_provenance.json').write_text(json.dumps({'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'items':prov},indent=2))

if __name__=='__main__': main()
