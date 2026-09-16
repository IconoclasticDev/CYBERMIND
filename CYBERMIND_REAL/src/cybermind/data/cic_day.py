"""Auditable, bounded-memory regeneration of a classic Ethernet PCAP day.

Labels use declared endpoints, service and schedule, never model features.
Unexplained traffic involving an attack endpoint is not called benign.
"""
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import struct
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from .pcap_extract import _new_flow, _row, _add_sequence, _scan_features

VICTIMS={'172.31.69.25','18.217.21.148'}
FTP={'172.31.70.4','18.221.219.4'}
SSH={'172.31.70.6','13.58.98.64'}
def epoch(time):
    return datetime.fromisoformat('2018-02-14T'+time+'+00:00').timestamp()

# The original minute-resolution schedule is interpreted as whole minutes.
# UTC+4 conversion from source wall-clock times is checked against raw packets.
SCHEDULE=[('FTP-BRUTEFORCE',FTP,21,epoch('14:32:00'),epoch('16:10:00')),
          ('SSH-BRUTEFORCE',SSH,22,epoch('18:01:00'),epoch('19:32:00'))]


def packets(path):
    """Yield every capture record; malformed/truncated IPv4 raises explicitly."""
    with Path(path).open('rb') as f:
        header=f.read(24)
        if len(header)!=24 or header[:4] not in (b'\xd4\xc3\xb2\xa1',b'\xa1\xb2\xc3\xd4'):
            raise ValueError('Expected classic microsecond PCAP')
        order='<' if header[:4]==b'\xd4\xc3\xb2\xa1' else '>'
        if struct.unpack_from(order+'I',header,20)[0]!=1:raise ValueError('Only Ethernet link type is supported')
        previous=None
        while record:=f.read(16):
            if len(record)!=16:raise ValueError('Truncated PCAP record header')
            seconds,micros,length,wire=struct.unpack(order+'4I',record)
            if length>16*1024*1024:raise ValueError('Invalid capture record size')
            raw=f.read(length)
            if len(raw)!=length:raise ValueError('Truncated PCAP record')
            t=seconds+micros/1e6
            if previous is not None and t<previous:raise ValueError('Capture not chronological')
            previous=t
            if len(raw)<14:raise ValueError('Truncated Ethernet frame')
            offset=14;protocol=struct.unpack_from('!H',raw,12)[0]
            while protocol in (0x8100,0x88a8):
                if len(raw)<offset+4:raise ValueError('Truncated VLAN header')
                protocol=struct.unpack_from('!H',raw,offset+2)[0];offset+=4
            if protocol!=0x0800:
                yield {'time':t,'skip':'non_ipv4','captured_bytes':length};continue
            if len(raw)<offset+20:raise ValueError('Truncated IPv4 header')
            ip=raw[offset:];ihl=(ip[0]&15)*4;total=struct.unpack_from('!H',ip,2)[0]
            if ip[0]>>4!=4 or ihl<20:raise ValueError('Invalid/truncated IPv4 packet')
            # Linux TCP segmentation offload captures can contain a complete host-side
            # super-packet with an IPv4 total-length field of zero. Accept only the
            # auditable signature seen in the source captures: the complete record is
            # present (caplen == wirelen), TCP is declared, and a full TCP header exists.
            # No source byte is changed and downstream provenance counts every use.
            offload_total_zero = total == 0 and length == wire and ip[9] == 6 and len(ip) >= ihl + 20
            if offload_total_zero:total=len(ip)
            if total<ihl or len(ip)<total:raise ValueError('Invalid/truncated IPv4 packet')
            flags=struct.unpack_from('!H',ip,6)[0];proto=ip[9]
            src=str(ipaddress.IPv4Address(ip[12:16]));dst=str(ipaddress.IPv4Address(ip[16:20]))
            # Fragment reassembly is not silently approximated as complete transport features.
            if flags&0x3fff:
                yield {'time':t,'skip':'fragmented_ipv4','captured_bytes':length};continue
            sport=dport=seq=tcpflags=window=0;transport=ip[ihl:total];payload=len(transport)
            if proto==6:
                if len(transport)<20:raise ValueError('Truncated TCP header')
                sport,dport,seq=struct.unpack_from('!HHI',transport)
                tcp_header=(transport[12]>>4)*4
                if tcp_header<20 or tcp_header>len(transport):raise ValueError('Invalid TCP data offset')
                tcpflags=transport[13];window=struct.unpack_from('!H',transport,14)[0];payload=len(transport)-tcp_header
            elif proto==17:
                if len(transport)<8:raise ValueError('Truncated UDP header')
                sport,dport,udp_length=struct.unpack_from('!HHH',transport)
                if udp_length<8 or udp_length>len(transport):raise ValueError('Invalid UDP length')
                payload=udp_length-8
            yield {'time':t,'src':src,'dst':dst,'proto':proto,'sport':sport,'dport':dport,
                   'ttl':ip[8],'df':bool(flags&0x4000),'payload':payload,'window':window,
                   'tcpflags':tcpflags,'seq':seq,'captured_bytes':length,
                   'ipv4_total_length_zero_offload':offload_total_zero}


def label_packet(p):
    for label,attackers,port,start,end in SCHEDULE:
        endpoint=(p['src'] in attackers and p['dst'] in VICTIMS and p['dport']==port) or (p['dst'] in attackers and p['src'] in VICTIMS and p['sport']==port)
        if endpoint and p['proto']==6 and start<=p['time']<end:
            return label
    if p['src'] in FTP|SSH or p['dst'] in FTP|SSH:
        return 'UNKNOWN_SCHEDULE_MISMATCH'
    return 'BENIGN'


def regenerate(path, output, report_path):
    output=Path(output)
    report_path=Path(report_path)
    partial=output.with_name(output.name+'.partial')
    if any(p.exists() for p in (output,partial,report_path)):
        raise FileExistsError('Preserve earlier regeneration output, partial output, and report')
    output.parent.mkdir(parents=True,exist_ok=True)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    flows={};scans={};bucket=None;writer=None;rows_count=0;counts=Counter();labels=Counter();spans={};flags=Counter()
    first=last=None
    def flush():
        nonlocal writer,rows_count
        if not flows:return
        rows=[]
        for (key,label),flow in flows.items():
            row=_row(key,flow,label)
            row.update(source='CIC-IDS2018',environment_id='CIC-IDS2018-victim-172.31.69.25',
                       label_method='official_schedule_endpoint_service_utc_plus4',
                       label_verified=label!='UNKNOWN_SCHEDULE_MISMATCH',capture_scope='complete_daily_victim_capture')
            rows.append(row)
        df=pd.DataFrame(rows).sort_values('timestamp',kind='stable')
        df['timestamp']=pd.to_datetime(df['timestamp'],utc=True)
        df['session_start']=pd.to_datetime(df['session_start'],utc=True)
        table=pa.Table.from_pandas(df,preserve_index=False)
        if writer is None:writer=pq.ParquetWriter(partial,table.schema,compression='zstd')
        writer.write_table(table);rows_count+=len(rows)
        flows.clear();scans.clear()
    try:
        for p in packets(path):
            t=p['time'];first=t if first is None else first;last=t;counts['capture_records']+=1
            if 'skip' in p:counts[p['skip']]+=1;continue
            current=int(t//60)
            if bucket is not None and current!=bucket:flush()
            bucket=current;counts['ipv4_packets_processed']+=1
            label=label_packet(p);labels[label]+=1
            key=(p['src'],p['dst'],p['proto'],p['sport'],p['dport'])
            pair=(p['src'],p['dst'],p['proto'])
            scan=scans.setdefault(pair,[])
            if p['proto'] in (6,17) and p['dport'] not in scan:scan.append(p['dport'])
            flow=flows.setdefault((key,label),_new_flow(t))
            if flow['packets']:flow['iats'].append(t-flow['last'])
            flow['last']=t;flow['packets']+=1;flow['bytes']+=p['captured_bytes'];flow['ttls'].append(p['ttl'])
            flow['df']+=p['df'];flow['payloads'].append(p['payload']);flow['scan']=_scan_features(scan)
            if p['proto']==6:
                flow['windows'].append(p['window']);_add_sequence(flow,p['seq'],p['payload']+bool(p['tcpflags']&2)+bool(p['tcpflags']&1))
            if p['src'] in FTP|SSH or p['dst'] in FTP|SSH:
                attack=p['src'] if p['src'] in FTP|SSH else p['dst'];port=p['dport'] if p['src']==attack else p['sport']
                name=f'{attack}:{port}';span=spans.setdefault(name,{'first_utc_epoch':t,'last_utc_epoch':t,'packets':0})
                span['last_utc_epoch']=t;span['packets']+=1
                flags[f'{name}:{p["tcpflags"]}']+=1
            if counts['capture_records']%250000==0:print(dict(counts),flush=True)
        flush()
    except Exception as exc:
        # A failed extraction remains inspectable but must never look complete.
        # Do not skip malformed records or flush an unfinished window to pass.
        failure={'status':'failed','error_type':type(exc).__name__,'error':str(exc),
                 'source_capture':str(path),'requested_output':str(output),
                 'partial_output':str(partial) if writer is not None else None,
                 'counts':dict(counts),'completed_rows':rows_count,
                 'unflushed_flow_count':len(flows),'full_capture_processed':False}
        with report_path.open('x',encoding='utf-8') as report_file:
            json.dump(failure,report_file,indent=2)
        raise
    finally:
        if writer is not None:writer.close()
    report={'status':'complete','full_capture_processed':True,'counts':dict(counts),'packet_labels':dict(labels),'rows':rows_count,'first_utc_epoch':first,'last_utc_epoch':last,
            'attacker_service_spans':spans,'attacker_tcp_flags':dict(flags),'window_seconds':60,
            'scope':'Complete victim-host capture; all capture records accounted for; non-IPv4 and fragments excluded explicitly',
            'schedule_source':'https://www.unb.ca/cic/datasets/ids-2018.html','schedule_clock_offset_hours_to_utc':4,
            'time_convention':'Original wall-clock schedule plus four hours; finish minute inclusive, next minute exclusive',
            'full_schedule_coverage':labels['UNKNOWN_SCHEDULE_MISMATCH']==0,
            'notes':'BENIGN means outside declared attacker endpoints under this schedule, not independent ground truth certification. FTP/SSH labels describe attempts, not successful compromise.'}
    if partial.exists():partial.rename(output)
    with report_path.open('x',encoding='utf-8') as report_file:
        json.dump(report,report_file,indent=2)
    return report
