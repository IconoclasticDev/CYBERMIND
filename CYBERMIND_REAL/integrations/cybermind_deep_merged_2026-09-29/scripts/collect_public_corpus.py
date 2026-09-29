#!/usr/bin/env python3
"""Public-source acquisition helper.

Downloads lightweight knowledge bases automatically and creates a manifest for the
large research datasets whose official portals may require a form/manual acceptance.
Dataset downloads can be supplied by direct URLs via environment variables.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
KNOW = ROOT / "knowledge" / "raw"
RAW = ROOT / "data" / "raw"

LANDING = {
    "CIC-IDS2017": "https://www.unb.ca/cic/datasets/ids-2017.html",
    "CICIoT2023": "https://www.unb.ca/cic/datasets/iotdataset-2023.html",
    "UNSW-NB15": "https://research.unsw.edu.au/projects/unsw-nb15-dataset",
    "CTU-13": "https://www.stratosphereips.org/datasets-ctu13",
    "LANL": "https://csr.lanl.gov/data/cyber1/",
    "DARPA1998": "https://www.ll.mit.edu/r-d/datasets/1998-darpa-intrusion-detection-evaluation-dataset",
    "DARPA1999": "https://www.ll.mit.edu/r-d/datasets/1999-darpa-intrusion-detection-evaluation-dataset",
    "NCIIPC": "https://www.nciipc.gov.in/",
}
DIRECT_ENV = {
    "CIC-IDS2017": "CYBERMIND_URL_CIC2017",
    "CICIoT2023": "CYBERMIND_URL_CICIOT2023",
    "UNSW-NB15": "CYBERMIND_URL_UNSW_NB15",
    "CTU-13": "CYBERMIND_URL_CTU13",
    "LANL": "CYBERMIND_URL_LANL",
    "DARPA1998": "CYBERMIND_URL_DARPA1998",
    "DARPA1999": "CYBERMIND_URL_DARPA1999",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def fetch(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "CYBERMIND-research-downloader/1.0"})
    with urlopen(req, timeout=180) as r, out.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--knowledge-only", action="store_true")
    ap.add_argument("--source", action="append", choices=sorted(list(LANDING) + ["CIC-IDS2018", "ATT&CK", "CAPEC", "NVD"]))
    ap.add_argument("--cic2018-prefix", default="")
    args = ap.parse_args()
    chosen = args.source or ["ATT&CK", "CAPEC", "NVD", "CIC-IDS2018", "CIC-IDS2017", "UNSW-NB15", "CTU-13", "CICIoT2023", "LANL", "DARPA1998", "DARPA1999"]
    KNOW.mkdir(parents=True, exist_ok=True)
    (RAW / "sources").mkdir(parents=True, exist_ok=True)
    manifest = []

    if "ATT&CK" in chosen:
        url = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
        out = KNOW / "enterprise-attack.json"
        try:
            fetch(url, out); manifest.append({"source":"ATT&CK","type":"knowledge","url":url,"path":str(out.relative_to(ROOT)),"sha256":sha256(out)})
        except Exception as e: manifest.append({"source":"ATT&CK","type":"knowledge","url":url,"status":"manual_retry","error":str(e)})

    if "CAPEC" in chosen:
        url = "https://capec.mitre.org/data/archive/capec_latest.zip"
        out = KNOW / "capec_latest.zip"
        try:
            fetch(url, out); manifest.append({"source":"CAPEC","type":"knowledge","url":url,"path":str(out.relative_to(ROOT)),"sha256":sha256(out)})
        except Exception as e: manifest.append({"source":"CAPEC","type":"knowledge","url":url,"status":"manual_retry","error":str(e)})

    if "NVD" in chosen:
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0?startIndex=0&resultsPerPage=2000"
        out = KNOW / "nvd_cves_page_0.json"
        try:
            fetch(url, out); manifest.append({"source":"NVD","type":"knowledge","url":url,"path":str(out.relative_to(ROOT)),"sha256":sha256(out)})
        except Exception as e: manifest.append({"source":"NVD","type":"knowledge","url":url,"status":"manual_retry","error":str(e)})

    if "CIC-IDS2018" in chosen:
        dest = RAW / "CIC-IDS-2018"; dest.mkdir(parents=True, exist_ok=True)
        if not any(dest.rglob("*")):
            cmd = ["aws", "s3", "sync", "--no-sign-request", "s3://cse-cic-ids2018/" + args.cic2018_prefix, str(dest)]
            try:
                subprocess.run(cmd, check=True); manifest.append({"source":"CIC-IDS2018","type":"dataset","method":"aws_s3_sync","uri":"s3://cse-cic-ids2018/" + args.cic2018_prefix,"path":str(dest.relative_to(ROOT))})
            except Exception as e: manifest.append({"source":"CIC-IDS2018","type":"dataset","status":"manual_retry","error":str(e),"uri":"s3://cse-cic-ids2018/"})
        else:
            manifest.append({"source":"CIC-IDS2018","type":"dataset","status":"already_present","path":str(dest.relative_to(ROOT))})

    for source in [s for s in chosen if s in LANDING and s != "CIC-IDS2018"]:
        env_name = DIRECT_ENV.get(source)
        url = os.getenv(env_name, "") if env_name else ""
        outdir = RAW / source.replace("/", "_")
        outdir.mkdir(parents=True, exist_ok=True)
        if args.knowledge_only:
            continue
        if url:
            filename = url.rstrip("/").split("/")[-1] or (source + ".download")
            out = outdir / filename.split("?")[0]
            try:
                fetch(url, out); manifest.append({"source":source,"type":"dataset","method":"direct_url_env","url":url,"path":str(out.relative_to(ROOT)),"sha256":sha256(out)})
            except Exception as e: manifest.append({"source":source,"type":"dataset","status":"manual_retry","error":str(e),"url":url})
        else:
            manifest.append({"source":source,"type":"dataset","status":"landing_page_required","landing_page":LANDING[source],"note":"Provide a direct download URL via the documented environment variable or download from the official page into this directory."})

    path = ROOT / "data/manifests" / "public_collection_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"generated_at_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),"items":manifest}, indent=2))
    print(path)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
