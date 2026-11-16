"""Checks at the native dependency/object boundary, including hostile inputs."""
import io
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit
import fetch


def archive(body, name='unit.o/'):
    header = f'{name:<16}{0:<12}{0:<6}{0:<6}{100644:<8}{len(body):<10}`\n'.encode()
    return b'!<arch>\n' + header + body + (b'\n' if len(body) & 1 else b'')


class Inputs(unittest.TestCase):
    def test_elf_archive_and_wrong_machine(self):
        body = bytearray(64)
        body[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<HH', body, 16, 1, 62)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.a'
            path.write_bytes(archive(body))
            self.assertEqual(audit.archive_members(path), 1)
            struct.pack_into('<H', body, 18, 183)  # AArch64 must not pass an x86-64 claim.
            path.write_bytes(archive(body))
            with self.assertRaisesRegex(ValueError, 'non-ELF64'):
                audit.archive_members(path)

    def test_windows_bitcode_empty_and_truncated_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.a'
            for data in (archive(b'MZ' + bytes(64)), archive(b'BC' + bytes(64)),
                         b'!<arch>\n', archive(bytes(64))[:-5], b'not ar'):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    audit.archive_members(path)

    def test_corrupt_archive_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fetch, 'CACHE', Path(temp)):
            target = Path(temp) / 'downloads/input.tar'
            target.parent.mkdir()
            target.write_bytes(b'changed upstream bytes')
            with self.assertRaisesRegex(ValueError, 'untrusted'):
                fetch.pinned_archive(dict(archive=target.name, sha256='0' * 64))

    def test_extraction_paths_and_links(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fetch, 'CACHE', Path(temp)):
            for name, link in [('source/../escape', False), ('source/dir/link', True)]:
                path = Path(temp) / 'input.tar'
                with tarfile.open(path, 'w') as bundle:
                    member = tarfile.TarInfo(name)
                    if link:
                        member.type, member.linkname = tarfile.SYMTYPE, '../../escape'
                        bundle.addfile(member)
                    else:
                        member.size = 1
                        bundle.addfile(member, io.BytesIO(b'x'))
                with self.assertRaises(ValueError):
                    fetch.extract(dict(folder='extracted', prefix='source'), path)
                self.assertFalse((Path(temp) / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
