"""Acquire a complete daily victim capture from a ZIP member, with CRC verification."""
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.request
import zlib

ROOT=Path(__file__).resolve().parents[1]


def main():
    directory=json.loads((ROOT/'examples/one_day_join/archive_directory.json').read_text(encoding='utf-8'))
    member=next(x for x in directory['entries'] if x['name']=='pcap/UCAP172.31.69.25')
    url=directory['url']; offset=member['offset']
    request=urllib.request.Request(url,headers={'Range':f'bytes={offset}-{offset+29}'})
    with urllib.request.urlopen(request,timeout=60) as response:
        if response.status!=206: raise ValueError('Expected HTTP range response')
        header=response.read(31)
    if len(header)!=30 or header[:4]!=b'PK\x03\x04':raise ValueError('Invalid ZIP member header')
    fields=struct.unpack('<4s5H3I2H',header)
    if fields[2]&1 or fields[3]!=8:raise ValueError('Unsupported encrypted/non-deflate ZIP member')
    start=offset+30+fields[-2]+fields[-1]
    folder=ROOT/'data/raw/CIC-IDS-2018/one_day_2018-02-14';folder.mkdir(parents=True,exist_ok=True)
    compressed=folder/'victim.deflate.partial'
    target=folder/'UCAP172.31.69.25.pcap'
    if target.exists():raise FileExistsError('Capture already exists; verify manifest instead of overwriting')
    total=member['compressed_bytes'];begin=time.monotonic()
    for attempt in range(8):
        have=compressed.stat().st_size if compressed.exists() else 0
        if have==total:break
        if have>total:raise ValueError('Partial file exceeds expected member size')
        request=urllib.request.Request(url,headers={'Range':f'bytes={start+have}-{start+total-1}'})
        try:
            with urllib.request.urlopen(request,timeout=90) as response:
                if response.status!=206:raise ValueError('Server ignored range')
                expected=f'bytes {start+have}-{start+total-1}/{directory["archive_bytes"]}'
                if response.headers.get('Content-Range')!=expected:raise ValueError('Wrong content range')
                with compressed.open('ab') as stream:
                    while chunk:=response.read(4*1024*1024):
                        stream.write(chunk);have+=len(chunk)
                        print(f'Capture compressed bytes {have}/{total}',flush=True)
        except (OSError,TimeoutError) as error:
            print(f'Retry {attempt+1}: {error}',flush=True)
    if compressed.stat().st_size!=total:raise ValueError('Incomplete capture acquisition')
    decoder=zlib.decompressobj(-15);crc=0;count=0;sha=hashlib.sha256()
    temporary=target.with_suffix('.pcap.partial')
    with compressed.open('rb') as source,temporary.open('wb') as destination:
        while chunk:=source.read(1024*1024):
            decoded=decoder.decompress(chunk)
            count+=len(decoded);crc=zlib.crc32(decoded,crc);sha.update(decoded);destination.write(decoded)
        decoded=decoder.flush();count+=len(decoded);crc=zlib.crc32(decoded,crc);sha.update(decoded);destination.write(decoded)
    if not decoder.eof or decoder.unused_data or count!=member['bytes'] or f'{crc:08x}'!=member['crc32']:
        raise ValueError('Complete member CRC/length verification failed')
    temporary.replace(target)
    result={'source_url':url,'member':member,'http_range_start':start,'scope':'Complete Feb 14 victim-host capture, not all 450 environment captures',
            'capture':str(target.relative_to(ROOT)),'capture_bytes':count,'sha256':sha.hexdigest(),'crc32':f'{crc:08x}',
            'complete_member_verified':True,'seconds':time.monotonic()-begin}
    (ROOT/'examples/one_day_join/acquisition.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
