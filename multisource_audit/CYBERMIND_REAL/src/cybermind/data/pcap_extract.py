"""Safe offline PCAP feature aggregation.

This module only reads packet captures; it does not generate or transmit traffic.
It creates flow-like rows with endpoint identity for graph construction.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import math
import pandas as pd

def pcap_to_dataframe(path: str|Path, label: str='PCAP_EVENT') -> pd.DataFrame:
    try:
        from scapy.all import IP, TCP, UDP, PcapReader
    except Exception as e:
        raise RuntimeError('scapy is required for PCAP extraction') from e
    flows=defaultdict(lambda: {'first':None,'last':None,'packets':0,'bytes':0,'src_port':0,'dst_port':0,'protocol':0,'iat_sum':0.,'iat_n':0})
    with PcapReader(str(path)) as reader:
        for pkt in reader:
            if not pkt.haslayer(IP): continue
            ip=pkt[IP]; src=str(ip.src); dst=str(ip.dst); proto=int(ip.proto)
            sport=dport=0
            if pkt.haslayer(TCP): sport=int(pkt[TCP].sport); dport=int(pkt[TCP].dport)
            elif pkt.haslayer(UDP): sport=int(pkt[UDP].sport); dport=int(pkt[UDP].dport)
            key=(src,dst,proto,sport,dport)
            t=float(pkt.time); n=int(len(pkt)); f=flows[key]
            if f['first'] is None: f['first']=t
            if f['last'] is not None: f['iat_sum'] += max(0.,t-f['last']); f['iat_n'] += 1
            f['last']=t; f['packets']+=1; f['bytes']+=n; f['src_port']=sport; f['dst_port']=dport; f['protocol']=proto
    rows=[]
    for (src,dst,proto,sport,dport),f in flows.items():
        dur=max(0.,f['last']-f['first']) if f['first'] is not None else 0.
        rows.append({'timestamp':pd.to_datetime(f['first'],unit='s'),'src':src,'dst':dst,'protocol':float(proto),'src_port':float(sport),'dst_port':float(dport),'duration':dur,
                     'bytes_fwd':float(f['bytes']),'bytes_bwd':0.,'packets_fwd':float(f['packets']),'packets_bwd':0.,'mean_fwd_iat':f['iat_sum']/max(f['iat_n'],1),'mean_bwd_iat':0.,
                     'flow_bytes_s':f['bytes']/max(dur,1e-6),'flow_packets_s':f['packets']/max(dur,1e-6),'label':label,'infiltration':1.,'stage':1})
    return pd.DataFrame(rows)
