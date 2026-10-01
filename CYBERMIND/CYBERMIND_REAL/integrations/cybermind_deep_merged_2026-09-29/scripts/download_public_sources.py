#!/usr/bin/env python3
"""Download/prepare only what is publicly and programmatically accessible.
Large research datasets remain user-triggered because they may be tens/hundreds of GB or require a web form.
"""
from pathlib import Path
import argparse, json, subprocess, sys, urllib.request, zipfile, hashlib, time
ROOT=Path(__file__).resolve().parents[1]

SOURCES={
 'cic2018_s3':'s3://cse-cic-ids2018/',
 'cic2017':'http://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/MachineLearningCSV.zip',
 'ciciot2023':'http://cicresearch.ca/IOTDataset/CICIoT2023/Dataset/CSV/CICIoT2023.zip',
 'ctu13':'https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/CTU-13-Dataset.tar.bz2',
 'unsw_nb15_hf':'https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/main/UNSW_NB15_training-set.csv',
 'attack_enterprise':'https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json',
 'capec_latest':'https://capec.mitre.org/data/archive/capec_latest.zip',
 'nvd_cve_recent':'https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz',
}
# NOTE on manual-only sources (all still no-login, just not one stable scriptable URL,
# so they are deliberately left out of SOURCES rather than guessed at):
#  - UNSW-NB15 official host (research.unsw.edu.au) serves through a UNSW SharePoint
#    share link that changes shape periodically. The HuggingFace mirror above is the
#    same data and is the scripted default; use the official page as a fallback.
#  - DARPA 1998/99 sets are per-week files on ll.mit.edu, browse and grab the specific
#    week(s) you want from https://www.ll.mit.edu/r-d/datasets/1998-darpa-intrusion-detection-evaluation-dataset
#  - LANL "Comprehensive Multi-Source Cyber-Security Events" auth/proc/dns/flow files
#    are large per-file .gz downloads (up to tens of GB) listed at
#    https://csr.lanl.gov/data/cyber1/ -- open that page and wget the specific files
#    you need rather than the whole 12GB+ corpus.
# See data/manifests/DOWNLOAD_MATRIX.md for the full picture including these.

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
    # Every source below is a public, no-login direct download. See the note above
    # SOURCES for the two datasets (UNSW-NB15, DARPA) that don't have one stable
    # scriptable URL and are documented as manual grabs instead.
    dest_map={
        'cic2017': 'data/raw/CIC-IDS-2017/MachineLearningCSV.zip',
        'ciciot2023': 'data/raw/CICIoT2023/CICIoT2023.zip',
        'ctu13': 'data/raw/CTU-13/CTU-13-Dataset.tar.bz2',
        'unsw_nb15_hf': 'data/raw/UNSW-NB15/UNSW_NB15_training-set.csv',
        'lanl_auth_sample': 'data/raw/LANL/auth_sample.txt.gz',
        'nvd_cve_recent': 'knowledge/cve/nvdcve-1.1-recent.json.gz',
        'attack_enterprise': 'knowledge/mitre_attack/enterprise-attack.json',
        'capec_latest': 'knowledge/capec/capec_latest.zip',
    }
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
            out=ROOT/dest_map.get(name, f'data/raw/{name}/{name}')
            try:
                download_url(SOURCES[name],out); prov.append({'source':name,'url':SOURCES[name],'sha256':sha256(out),'bytes':out.stat().st_size})
            except Exception as e:
                print('WARNING',name,e)
    (ROOT/'data/manifests'/'download_provenance.json').write_text(json.dumps({'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'items':prov},indent=2))

if __name__=='__main__': main()
