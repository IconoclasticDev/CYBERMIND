"""Inspect an authoritative daily ZIP directory with bounded HTTP range reads."""
import argparse
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class RemoteArchive(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0
        self.requests = []

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        return self.position

    def tell(self):
        return self.position

    def read(self, count=-1):
        count = self.size-self.position if count < 0 else min(count, self.size-self.position)
        if count == 0:
            return b''
        if count < 0 or count > 16*1024*1024:
            raise ValueError('Archive metadata read exceeds 16 MiB limit')
        start = self.position
        request = urllib.request.Request(self.url, headers={'Range':f'bytes={start}-{start+count-1}'})
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 206:
                raise ValueError('Server did not honor bounded range request')
            data = response.read(count+1)
        if len(data) != count:
            raise ValueError('Unexpected range length')
        self.position += count
        self.requests.append({'start':start,'bytes':count})
        return data


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--date',default='14-02-2018')
    ap.add_argument('--output',default='examples/one_day_join/archive_directory.json')
    args=ap.parse_args()
    inventory=json.loads((ROOT/'examples/phase4/packet_availability/availability.json').read_text(encoding='utf-8'))
    record=next(r for r in inventory['pcap_archives'] if args.date in r['key'])
    url='https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/'+urllib.parse.quote(record['key'],safe='/')
    reader=RemoteArchive(url,record['bytes'])
    with zipfile.ZipFile(reader) as archive:
        entries=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'offset':i.header_offset,'crc32':f'{i.CRC:08x}','compression':i.compress_type} for i in archive.infolist()]
    result={'date':args.date,'url':url,'archive_bytes':record['bytes'],'entries':entries,'metadata_requests':reader.requests,'total_uncompressed_bytes':sum(i['bytes'] for i in entries)}
    output=ROOT/args.output;output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
