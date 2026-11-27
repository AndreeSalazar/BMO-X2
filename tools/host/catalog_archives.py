"""Bounded ZIP inventory. Archive entries are read into memory only."""

from collections import Counter
from io import BytesIO
import hashlib
from pathlib import PurePosixPath
import stat
import struct
import unicodedata
import zipfile
import zlib


MAX_MEMBERS = 2048
MAX_CENTRAL_BYTES = 2 * 1024 * 1024
MAX_MEMBER_BYTES = 2 * 1024 * 1024
MAX_EXPANDED_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 2
EOCD = struct.Struct('<4s4H2IH')


def directory_count(data):
    position = data.rfind(b'PK\x05\x06', max(0, len(data) - EOCD.size - 65535))
    if position < 0 or position + EOCD.size > len(data):
        raise zipfile.BadZipFile('No se encontro el directorio central.')
    _, disk, directory_disk, per_disk, count, size, _, comment = EOCD.unpack_from(data, position)
    if position + EOCD.size + comment != len(data) or disk or directory_disk or per_disk != count:
        raise zipfile.BadZipFile('Directorio central fuera del perfil ZIP.')
    if count > MAX_MEMBERS or size > MAX_CENTRAL_BYTES:
        raise zipfile.BadZipFile('Directorio central por encima del presupuesto ZIP.')
    return count


def path_checks(info, duplicates):
    name = info.orig_filename
    canonical = name.replace('\\', '/').rstrip('/')
    parts = canonical.split('/')
    findings = []
    if (not canonical or any(part in ('', '.', '..') or ':' in part or part.endswith((' ', '.'))
                             for part in parts) or '\\' in name):
        findings.append('RUTA_DE_ARCHIVO_NO_ADMITIDA')
    if any(unicodedata.category(char) in ('Cc', 'Cf') for char in name):
        findings.append('CARACTERES_DE_CONTROL_O_FORMATO')
    if duplicates[canonical.casefold()] > 1:
        findings.append('NOMBRE_DUPLICADO')
    kind = stat.S_IFMT(info.external_attr >> 16) if info.create_system == 3 else 0
    if kind and kind not in (stat.S_IFREG, stat.S_IFDIR):
        findings.append('ENLACE_U_OBJETO_ESPECIAL')
    if info.flag_bits & 1:
        findings.append('CIFRADO')
    return findings


def inspect_zip(data, classify, role_hint, name_findings, budget, depth=0):
    if depth >= MAX_DEPTH:
        return dict(Status='REVISION', Reason='Limite de profundidad ZIP.', Entries=[])
    try:
        expected = directory_count(data)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) != expected:
                raise zipfile.BadZipFile('Cantidad real distinta del directorio central.')
            if len(members) > budget['members']:
                return dict(Status='REVISION', Reason='Presupuesto global de entradas ZIP agotado.',
                            DeclaredEntries=len(members), Entries=[])
            budget['members'] -= len(members)
            duplicates = Counter(info.orig_filename.replace('\\', '/').rstrip('/').casefold()
                                 for info in members)
            entries = []
            complete = True
            for info in members:
                member_path = PurePosixPath(info.orig_filename.replace('\\', '/'))
                item = dict(Path=info.orig_filename, Bytes=info.file_size, CompressedBytes=info.compress_size,
                            RoleHint=role_hint(member_path))
                if warnings := name_findings(member_path):
                    item['NameFindings'] = warnings
                findings = path_checks(info, duplicates)
                if findings:
                    item.update(Category='DESCONOCIDO', Status='REVISION', Findings=findings)
                elif info.is_dir():
                    item.update(Category='DIRECTORIO', Status='METADATOS')
                elif (info.file_size > min(MAX_MEMBER_BYTES, budget['bytes']) or
                      info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    item.update(Category='DESCONOCIDO', Status='REVISION',
                                Reason='Tamano, presupuesto o metodo de compresion fuera del perfil.')
                else:
                    # Charge the read even if decompression or the CRC check fails.
                    budget['bytes'] -= info.file_size
                    try:
                        with archive.open(info) as reader:
                            content = reader.read(info.file_size + 1)
                        if len(content) != info.file_size:
                            raise zipfile.BadZipFile('Longitud del contenido distinta de la declarada.')
                    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error):
                        item.update(Category='DESCONOCIDO', Status='REVISION',
                                    Reason='Error de lectura o integridad del miembro ZIP.')
                    else:
                        item['SHA256'] = hashlib.sha256(content).hexdigest()
                        symbols = classify(content, member_path.suffix.lower(), item)
                        if symbols:
                            item['Imports'] = symbols
                        if item.get('Format') == 'ZIP':
                            item['Archive'] = inspect_zip(
                                content, classify, role_hint, name_findings, budget, depth + 1)
                if (item['Status'] in ('REVISION', 'BLOQUEADO') or item.get('ExtensionMismatch') or
                        item.get('NameFindings') or item.get('Archive', {}).get('Status') == 'REVISION'):
                    complete = False
                entries.append(item)
            return dict(Status='INVENTARIADO' if complete else 'REVISION', DeclaredEntries=expected, Entries=entries)
    except (zipfile.BadZipFile, NotImplementedError, UnicodeError, ValueError):
        return dict(Status='REVISION', Reason='ZIP invalido o directorio fuera del perfil.', Entries=[])
