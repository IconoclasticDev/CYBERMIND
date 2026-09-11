"""Copy every workspace entry, ZIP the copy, and verify hashes/CRC. No deletion."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import stat
import time
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
DESTINATION = Path(r'D:\Abhinav\College\SIH')
CHUNK = 4 * 1024 * 1024


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    context = SOURCE / 'SESSION_CONTEXT.md'
    if '<!-- SESSION_CONTEXT_READY_FOR_COPY -->' not in context.read_text(encoding='utf-8'):
        raise RuntimeError('Context must be complete before any copy starts.')
    files, directories, links = [], [], []
    def visit(directory):
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(SOURCE)
                if path.is_junction():
                    raise RuntimeError(f'Junction requires explicit preservation handling: {path}')
                if entry.is_symlink():
                    links.append((relative, os.readlink(path), path.is_dir()))
                elif entry.is_dir(follow_symlinks=False):
                    directories.append(relative)
                    visit(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append((relative, entry.stat(follow_symlinks=False)))
                else:
                    raise RuntimeError(f'Unsupported filesystem entry, nothing will be silently omitted: {path}')
    print('Inventorying the complete source tree, including hidden files and environments...', flush=True)
    visit(SOURCE)
    total_bytes = sum(info.st_size for _, info in files)
    print(f'Inventory: {len(files):,} files, {len(directories):,} directories, {len(links)} links, {total_bytes / 1024**3:.3f} GiB.', flush=True)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(DESTINATION).free < total_bytes * 2 + 1024**3:
        raise RuntimeError('Insufficient destination space for a full copy and ZIP.')
    name = SOURCE.name + '_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    copy = DESTINATION / name
    archive = DESTINATION / (name + '.zip')
    manifest = DESTINATION / (name + '_verification.json')
    if any(path.exists() for path in (copy, archive, manifest)):
        raise RuntimeError('Destination already exists; refusing to overwrite.')
    copy.mkdir()
    for relative in directories:
        (copy / relative).mkdir(parents=True, exist_ok=True)

    def copy_file(record):
        relative, before = record
        source, target = SOURCE / relative, copy / relative
        hasher = hashlib.sha256()
        with source.open('rb') as reader, target.open('xb') as writer:
            for chunk in iter(lambda: reader.read(CHUNK), b''):
                writer.write(chunk)
                hasher.update(chunk)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError(f'Source changed while backing up: {source}')
        shutil.copystat(source, target, follow_symlinks=False)
        return {'path': relative.as_posix(), 'bytes': before.st_size, 'sha256': hasher.hexdigest()}

    records = []
    last = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as executor:
        for record in executor.map(copy_file, files):
            records.append(record)
            if time.monotonic() - last > 10:
                print(f'Copied and source-hashed {len(records):,}/{len(files):,} files.', flush=True)
                last = time.monotonic()
    for relative, target, is_directory in links:
        os.symlink(target, copy / relative, target_is_directory=is_directory)
    print(f'Full copy complete: {copy}', flush=True)

    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as output:
        output.mkdir(SOURCE.name + '/')
        for relative in directories:
            output.mkdir(SOURCE.name + '/' + relative.as_posix() + '/')
        for index, record in enumerate(records, 1):
            path = copy / record['path']
            info = zipfile.ZipInfo.from_file(path, arcname=SOURCE.name + '/' + record['path'], strict_timestamps=False)
            info.compress_type = zipfile.ZIP_DEFLATED
            info._compresslevel = 1
            hasher = hashlib.sha256()
            with path.open('rb') as reader, output.open(info, 'w', force_zip64=True) as writer:
                for chunk in iter(lambda: reader.read(CHUNK), b''):
                    hasher.update(chunk)
                    writer.write(chunk)
            if hasher.hexdigest() != record['sha256']:
                raise RuntimeError(f'Copied content differs from source: {path}')
            if time.monotonic() - last > 10:
                print(f'ZIP: {index:,}/{len(records):,} files; copied SHA-256 matches source.', flush=True)
                last = time.monotonic()
        for relative, target, _ in links:
            info = zipfile.ZipInfo(SOURCE.name + '/' + relative.as_posix())
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(info, target.encode('utf-8'))
    # Restore directory timestamps only after creating their contents.
    for relative in reversed(directories):
        shutil.copystat(SOURCE / relative, copy / relative, follow_symlinks=False)
    shutil.copystat(SOURCE, copy, follow_symlinks=False)

    print('Verifying every ZIP entry (decompression and CRC)...', flush=True)
    with zipfile.ZipFile(archive) as zipped:
        expected = {SOURCE.name + '/'} | {SOURCE.name + '/' + p.as_posix() + '/' for p in directories}
        expected |= {SOURCE.name + '/' + record['path'] for record in records}
        expected |= {SOURCE.name + '/' + p.as_posix() for p, _, _ in links}
        if set(zipped.namelist()) != expected or len(zipped.namelist()) != len(expected):
            raise RuntimeError('ZIP entry list does not exactly match inventory.')
        for index, entry in enumerate(zipped.infolist(), 1):
            if not entry.is_dir():
                with zipped.open(entry) as reader:
                    while reader.read(CHUNK):
                        pass
            if time.monotonic() - last > 10:
                print(f'CRC verified {index:,}/{len(expected):,} ZIP entries.', flush=True)
                last = time.monotonic()
    if digest(context) != digest(copy / 'SESSION_CONTEXT.md'):
        raise RuntimeError('Context file changed or was copied incorrectly.')
    print('Computing final ZIP SHA-256...', flush=True)
    result = {
        'status': 'verified', 'completed_utc': datetime.now(timezone.utc).isoformat(),
        'source': str(SOURCE), 'copy': str(copy), 'zip': str(archive),
        'files': len(files), 'directories': len(directories), 'links': len(links),
        'source_bytes': total_bytes, 'zip_bytes': archive.stat().st_size,
        'zip_sha256': digest(archive), 'context_sha256': digest(context),
        'context_completed_before_copy': True, 'all_copy_hashes_match_source': True,
        'zip_inventory_and_all_crc_verified': True, 'excluded_paths': [],
        'file_manifest': records,
    }
    manifest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(result['zip_sha256'] + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'file_manifest'}, indent=2), flush=True)
    print(f'Verification manifest: {manifest}', flush=True)


if __name__ == '__main__':
    main()
