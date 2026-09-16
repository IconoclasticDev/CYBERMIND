"""Validate every canonical row; strict mode does not sample only a file prefix."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES


def validate_file(path, strict=False, require_packet_features=False):
    path=Path(path)
    batches=(b.to_pandas() for b in pq.ParquetFile(path).iter_batches(batch_size=100000)) if path.suffix=='.parquet' else pd.read_csv(path,chunksize=100000,low_memory=False)
    record={'file':str(path),'rows_checked':0,'invalid_endpoint_rows':0,'invalid_timestamp_rows':0,
            'invalid_label_rows':0,'unverified_label_rows':0,'invalid_packet_rows':0,'missing_required':[]}
    for df in batches:
        record['rows_checked']+=len(df)
        required=['timestamp','src','dst','label']+(list(PACKET_FEATURES) if require_packet_features else [])
        missing=[c for c in required if c not in df]
        record['missing_required']=sorted(set(record['missing_required'])|set(missing))
        if missing:continue
        endpoints=pd.Series(True,index=df.index)
        for col in ('src','dst'):
            endpoints &= df[col].notna() & ~df[col].astype(str).str.strip().str.lower().isin(['','nan','none','null'])
        record['invalid_endpoint_rows']+=int((~endpoints).sum())
        record['invalid_timestamp_rows']+=int(pd.to_datetime(df.timestamp,format='ISO8601',errors='coerce',utc=True).isna().sum())
        labels=df.label.fillna('').astype(str).str.strip()
        record['invalid_label_rows']+=int(labels.eq('').sum())
        if 'label_verified' in df:
            record['unverified_label_rows']+=int((~df.label_verified.astype(str).str.lower().isin(['true','1'])).sum())
        if require_packet_features:
            numeric=df[list(PACKET_FEATURES)].apply(pd.to_numeric,errors='coerce')
            valid=np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)&numeric.packet_features_available.eq(1).to_numpy()
            record['invalid_packet_rows']+=int((~valid).sum())
    errors=['missing_required'] if record['missing_required'] else []
    if not record['rows_checked']:errors.append('empty_input')
    if strict:
        errors += [key for key in ('invalid_endpoint_rows','invalid_timestamp_rows','invalid_label_rows','unverified_label_rows','invalid_packet_rows') if record[key]]
    record['errors']=errors;record['passed']=not errors
    return record


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--strict',action='store_true')
    ap.add_argument('--require-packet-features',action='store_true')
    ap.add_argument('--output',default=str(ROOT/'data/manifests/validation_report.json'))
    args=ap.parse_args();path=Path(args.input)
    files=sorted(path.rglob('*.parquet'))+sorted(path.rglob('*.csv')) if path.is_dir() else [path]
    report=[]
    for file in files:
        try:rec=validate_file(file,args.strict,args.require_packet_features)
        except Exception as error:rec={'file':str(file),'passed':False,'error':str(error)}
        report.append(rec);print(json.dumps(rec))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report and all(r['passed'] for r in report) else 1


if __name__=='__main__':raise SystemExit(main())
