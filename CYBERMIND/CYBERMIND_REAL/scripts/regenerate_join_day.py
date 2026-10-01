from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cybermind.data.cic_day import regenerate
if __name__=='__main__':
    result=regenerate(ROOT/'data/raw/CIC-IDS-2018/one_day_2018-02-14/UCAP172.31.69.25.pcap',ROOT/'data/one_day_join/events.parquet',ROOT/'examples/one_day_join/regeneration.json')
    print(json.dumps(result,indent=2))
