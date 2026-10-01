import importlib.util
from pathlib import Path
import json
import pandas as pd
import pytest
from scapy.all import Ether,IP,TCP,UDP,Raw,wrpcap
from cybermind.data.cic_day import packets,label_packet,regenerate,epoch
from cybermind.data.pcap_extract import pcap_to_dataframe,PACKET_FEATURES


def validator():
    spec=importlib.util.spec_from_file_location('join_validator',Path(__file__).resolve().parents[1]/'scripts/validate_dataset.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_native_capture_features_match_existing_scapy_extractor(tmp_path):
    capture=[]
    for i in range(3):
        packet=Ether()/IP(src='10.0.0.1',dst='10.0.0.2',ttl=60+i,flags='DF')/TCP(sport=12345,dport=80,seq=100+i*3,flags='PA',window=100+i)/Raw(b'abc')
        packet.time=epoch('13:00:00')+i*.25;capture.append(packet)
    path=tmp_path/'sample.pcap';wrpcap(str(path),capture)
    report=regenerate(path,tmp_path/'events.parquet',tmp_path/'report.json')
    actual=pd.read_parquet(tmp_path/'events.parquet');expected=pcap_to_dataframe(path,'BENIGN')
    assert report['counts']['capture_records']==3 and report['full_schedule_coverage']
    for name in list(PACKET_FEATURES)+['bytes_fwd','packets_fwd','duration','mean_fwd_iat']:
        assert actual[name].iloc[0]==pytest.approx(expected[name].iloc[0]),name
    assert validator().validate_file(tmp_path/'events.parquet',True,True)['passed']


def test_schedule_requires_endpoint_service_clock_and_handles_reverse():
    p={'src':'18.221.219.4','dst':'172.31.69.25','sport':40000,'dport':21,'proto':6,'time':epoch('15:00:00')}
    assert label_packet(p)=='FTP-BRUTEFORCE'
    reverse={**p,'src':p['dst'],'dst':p['src'],'sport':21,'dport':40000}
    assert label_packet(reverse)=='FTP-BRUTEFORCE'
    assert label_packet({**p,'time':epoch('16:10:30')})=='UNKNOWN_SCHEDULE_MISMATCH'
    assert label_packet({**p,'dport':22})=='UNKNOWN_SCHEDULE_MISMATCH'
    assert label_packet({**p,'src':'10.0.0.1'})=='BENIGN'


def test_validator_checks_beyond_old_ten_thousand_row_prefix(tmp_path):
    frame=pd.DataFrame({'timestamp':['2018-02-14T15:00:00Z']*10001,'src':'10.0.0.1','dst':'10.0.0.2','label':'BENIGN'})
    frame.loc[10000,'timestamp']='invalid'
    path=tmp_path/'events.csv';frame.to_csv(path,index=False)
    result=validator().validate_file(path,True)
    assert result['rows_checked']==10001 and result['invalid_timestamp_rows']==1 and not result['passed']


def test_unverified_schedule_labels_and_missing_packets_fail_strict(tmp_path):
    frame=pd.DataFrame({'timestamp':['2018-02-14T15:00:00Z'],'src':['a'],'dst':['b'],'label':['UNKNOWN_SCHEDULE_MISMATCH'],'label_verified':[False],**{n:[1.] for n in PACKET_FEATURES}})
    path=tmp_path/'events.parquet';frame.to_parquet(path)
    assert validator().validate_file(path,True,True)['errors']==['unverified_label_rows']
    frame['label_verified']=True;frame['ttl_mean']=float('nan');frame.to_parquet(path)
    assert 'invalid_packet_rows' in validator().validate_file(path,True,True)['errors']


def test_truncated_capture_preserves_failure_without_publishing_final_output(tmp_path):
    capture=[]
    for i in range(3):
        packet=Ether()/IP(src='10.0.0.1',dst='10.0.0.2')/TCP(sport=12345,dport=80)/Raw(b'abc')
        packet.time=epoch('13:00:00')+i*60
        capture.append(packet)
    source=tmp_path/'truncated.pcap'
    wrpcap(str(source),capture)
    source.write_bytes(source.read_bytes()[:-1])
    output=tmp_path/'events.parquet'; report=tmp_path/'report.json'
    with pytest.raises(ValueError,match='Truncated PCAP record'):
        regenerate(source,output,report)
    assert not output.exists()
    evidence=json.loads(report.read_text())
    assert evidence['status']=='failed' and not evidence['full_capture_processed']
    assert evidence['completed_rows']==1 and evidence['unflushed_flow_count']==1
    partial=Path(evidence['partial_output'])
    assert len(pd.read_parquet(partial))==1
    saved_partial=partial.read_bytes();saved_report=report.read_bytes()
    with pytest.raises(FileExistsError):
        regenerate(source,output,report)
    assert partial.read_bytes()==saved_partial and report.read_bytes()==saved_report


def test_success_publishes_only_completed_output(tmp_path):
    packet=Ether()/IP(src='10.0.0.1',dst='10.0.0.2')/UDP(sport=12345,dport=53)/Raw(b'abc')
    packet.time=epoch('13:00:00')
    source=tmp_path/'complete.pcap';wrpcap(str(source),[packet])
    output=tmp_path/'events.parquet'
    report=regenerate(source,output,tmp_path/'report.json')
    assert output.exists() and not output.with_name(output.name+'.partial').exists()
    assert report['status']=='complete' and report['full_capture_processed']
