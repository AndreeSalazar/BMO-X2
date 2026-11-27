"""Read-only intake of a stable directory before selecting SBEF inputs."""

from collections import defaultdict
import hashlib
from itertools import islice
import os
from pathlib import Path
import re
import stat
import unicodedata

from .catalog_archives import MAX_EXPANDED_BYTES, MAX_MEMBERS, inspect_zip
from .diagnostics import Rejection
from .importers.elf import MAX_ELF, pack_elf
from .importers.pe import probe_pe
from .pe_admission import import_requirements
from .sbef.format import inspect
from .toolchains.windows_catalog import dependency_family


MAX_ENTRIES = 2048
MAX_TOTAL_BYTES = 64 * 1024 * 1024
DEEP_ENTRIES = 32768
DEEP_TOTAL_BYTES = 256 * 1024 * 1024
RESOURCE_HEADERS = (
    (b'\x89PNG\r\n\x1a\n', 'PNG'),
    (b'%PDF-', 'PDF'),
    (b'SQLite format 3\0', 'SQLite'),
    (b'\x1f\x8b\x08', 'GZIP'),
    (b'PK\x03\x04', 'ZIP'),
    (b'PK\x05\x06', 'ZIP'),
)
TEXT_SUFFIXES = {'.txt', '.md', '.ini', '.cfg', '.json', '.toml', '.csv', '.xml', '.yaml', '.yml'}
SOURCE_SUFFIXES = {'.c', '.h', '.cpp', '.hpp', '.rs', '.py', '.ps1', '.js', '.asm', '.s', '.casm'}


def role_hint(path):
    suffix = path.suffix.lower()
    name = path.stem.casefold()
    if suffix == '.exe':
        if any(word in name for word in ('launcher', 'setup', 'installer', 'updater')):
            return 'LANZADOR_O_INSTALADOR'
        return 'EJECUTABLE'
    if suffix in ('.dll', '.so', '.asi', '.ocx'):
        return 'MODULO'
    if suffix in ('.pak', '.rpf', '.vpk', '.ucas', '.utoc', '.zip', '.7z', '.rar'):
        return 'CONTENEDOR_DE_RECURSOS'
    if suffix in ('.ini', '.cfg', '.json', '.toml', '.xml', '.yaml', '.yml'):
        return 'CONFIGURACION'
    if suffix in ('.bat', '.cmd', '.ps1', '.vbs', '.js', '.lua', '.py'):
        return 'SCRIPT'
    if suffix in ('.png', '.dds', '.jpg', '.jpeg', '.ogg', '.wav', '.mp4', '.webm'):
        return 'RECURSO_MULTIMEDIA'
    return 'SIN_INDICIO'


def name_findings(path):
    findings = []
    if any(unicodedata.category(char) in ('Cc', 'Cf') for char in path.name):
        findings.append('CARACTERES_DE_CONTROL_O_FORMATO')
    if path.suffix.lower() in ('.exe', '.scr', '.bat', '.cmd', '.ps1', '.vbs') and (
        Path(path.stem).suffix.lower() in TEXT_SUFFIXES | {'.pdf', '.jpg', '.png', '.docx', '.zip'}
    ):
        findings.append('DOBLE_EXTENSION_EJECUTABLE')
    return findings


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def fingerprint(info):
    # Windows can report creation time through lstat and change time through fstat.
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size, info.st_mtime_ns


def unknown(record, reason, **extra):
    record.update(Category='DESCONOCIDO', Status='REVISION', Reason=reason, **extra)


def classify(data, suffix, record):
    try:
        if data.startswith(b'MZ'):
            pe = probe_pe(data)
            kind = pe['ImageKind']
            record.update(Category='BIBLIOTECA' if kind == 'DLL' else 'EJECUTABLE',
                          Format=f"{pe['SourceFormat']} {pe['Architecture']}",
                          ImageKind=kind, Architecture=pe['Architecture'],
                          Status='ADMISIBLE' if pe['CanPack'] else 'BLOQUEADO',
                          Blockers=pe['Blockers'],
                          ExtensionMismatch=suffix != ('.dll' if kind == 'DLL' else '.exe'))
            requirements = import_requirements(pe)
            if requirements['Status'] == 'invalid':
                record['ImportError'] = requirements['Error']
                return []
            return [item for group in requirements['Groups'] for item in group['Imports']]
        if data.startswith(b'\x7fELF'):
            pack_elf(data, abi=1)
            record.update(Category='EJECUTABLE', Format='ELF64 x86-64', Status='ADMISIBLE',
                          ExtensionMismatch=bool(suffix and suffix != '.elf'))
            return []
        if data.startswith(b'SBEF'):
            package = inspect(data)
            record.update(Category='PAQUETE', Format='SBEF', Status='ESTRUCTURA_VALIDADA',
                          AbiVersion=package['AbiVersion'],
                          ExtensionMismatch=suffix not in ('.sbf', '.sbef'))
            return []
    except Rejection as error:
        unknown(record, 'La cabecera reconocida no paso el importador HOST.', Rejection=error.report())
        return []

    for signature, name in RESOURCE_HEADERS:
        if data.startswith(signature):
            record.update(Category='DATOS', Format=name, Status='FIRMA_RECONOCIDA')
            return []
    if suffix in TEXT_SUFFIXES | SOURCE_SUFFIXES and b'\0' not in data:
        try:
            data.decode('utf-8-sig')
        except UnicodeDecodeError:
            pass
        else:
            record.update(Category='FUENTE' if suffix in SOURCE_SUFFIXES else 'DATOS',
                          Format='Texto UTF-8', Status='REVISION')
            return []
    unknown(record, 'Sin formato reconocido por este inventario.')
    return []


def catalog_directory(root, *, deep=False, game=None):
    if game is not None:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _-]{0,63}', game) or game != game.rstrip():
            raise Rejection('HOST-CATALOG-TITLE', 0, 'game')
        if re.fullmatch(r'AUX|CON|NUL|PRN|COM[0-9]|LPT[0-9]', game, re.IGNORECASE):
            raise Rejection('HOST-CATALOG-TITLE', 0, 'game')
        deep = True
    root_info = root.lstat()
    if is_link(root_info) or not stat.S_ISDIR(root_info.st_mode):
        raise Rejection('HOST-CATALOG-ROOT', 0, 'root')
    root = root.resolve(strict=True)
    entries = []
    imports = {}
    libraries = defaultdict(list)
    pending = [root]
    visited = 0
    total = 0
    truncated = False
    max_entries = DEEP_ENTRIES if deep else MAX_ENTRIES
    byte_budget = DEEP_TOTAL_BYTES if deep else MAX_TOTAL_BYTES
    archive_budget = {'bytes': MAX_EXPANDED_BYTES, 'members': MAX_MEMBERS}
    while pending:
        directory = pending.pop()
        current = directory.lstat()
        if is_link(current) or not stat.S_ISDIR(current.st_mode):
            raise Rejection('HOST-CATALOG-DIRECTORY-CHANGED', 0, 'root')
        with os.scandir(directory) as children:
            paths = sorted(item.path for item in islice(children, max_entries - visited + 1))
        children = list(map(Path, paths))
        remaining = max_entries - visited
        if len(children) > remaining:
            if not deep:
                raise Rejection('HOST-CATALOG-ENTRIES', 0, 'root')
            truncated = True
            children = children[:remaining]
        visited += len(children)
        for path in children:
            relative = path.relative_to(root).as_posix()
            record = dict(Path=relative)
            if deep:
                record['RoleHint'] = role_hint(path)
                if findings := name_findings(path):
                    record['NameFindings'] = findings
            try:
                info = path.lstat()
                if is_link(info):
                    unknown(record, 'Enlace o punto de reanalisis omitido.')
                elif stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                    continue
                elif not stat.S_ISREG(info.st_mode):
                    unknown(record, 'Objeto distinto de un archivo normal.')
                elif info.st_size > MAX_ELF:
                    unknown(record, 'Archivo por encima del limite de lectura.', Bytes=info.st_size)
                elif deep and info.st_size > byte_budget - total:
                    unknown(record, 'Presupuesto global de lectura agotado.', Bytes=info.st_size)
                else:
                    if info.st_size > byte_budget - total:
                        raise Rejection('HOST-CATALOG-BUDGET', 0, 'root')
                    with path.open('rb') as file:
                        opened = os.fstat(file.fileno())
                        data = file.read(info.st_size + 1) if fingerprint(opened) == fingerprint(info) else None
                    total += len(data) if data is not None else 0
                    if data is None or len(data) != info.st_size or fingerprint(path.lstat()) != fingerprint(info):
                        unknown(record, 'El archivo cambio durante el inventario.')
                    else:
                        record.update(Bytes=len(data), SHA256=hashlib.sha256(data).hexdigest())
                        symbols = classify(data, path.suffix.lower(), record)
                        if deep and record.get('Format') == 'ZIP':
                            record['Archive'] = inspect_zip(
                                data, classify, role_hint, name_findings, archive_budget)
                        if symbols:
                            imports[relative] = record['Architecture'], symbols
                        if record.get('ImageKind') == 'DLL':
                            libraries[record['Architecture'], path.name.lower()].append(relative)
            except OSError:
                unknown(record, 'El archivo no pudo leerse.')
            entries.append(record)

    edges = []
    launch_dependencies = defaultdict(list)
    for source, (architecture, symbols) in sorted(imports.items()):
        by_dll = defaultdict(list)
        for symbol in symbols:
            by_dll[symbol['DLL'].lower()].append(symbol)
        for dll, required in sorted(by_dll.items()):
            candidates = sorted(libraries[architecture, dll])
            tested = sum(symbol['Status'] == 'available_in_fixture' for symbol in required)
            edge = dict(From=source, DLL=dll, Symbols=[
                symbol.get('Name', f'#{symbol.get("Ordinal")}') for symbol in required],
                LocalCandidates=candidates, FixtureSymbols=tested,
                Status=('AMBIGUA' if len(candidates) > 1 else 'CANDIDATA_LOCAL' if candidates else
                        'RUNTIME_ACOTADO' if tested else 'PENDIENTE'))
            if deep:
                level, family = dependency_family(dll)
                edge.update(Family=family or 'unknown', Level=level,
                            FamilyEvidence='Nombre de DLL o prefijo API Set del catalogo HOST.' if family
                            else 'Dependencia declarada fuera del catalogo Windows.')
                edge['SymbolsWithoutRuntimeEvidence'] = [
                    symbol.get('Name', f'#{symbol.get("Ordinal")}') for symbol in required
                    if symbol['Status'] != 'available_in_fixture']
                launch_dependencies[source].append(dll)
            edges.append(edge)
    entries.sort(key=lambda record: record['Path'])
    groups = {category: [record['Path'] for record in entries if record['Category'] == category]
              for category in ('EJECUTABLE', 'BIBLIOTECA', 'PAQUETE', 'FUENTE', 'DATOS', 'DESCONOCIDO')}
    report = dict(Root=str(root), Scope='Inspeccion estatica HOST de formatos, huellas y dependencias.',
                  Files=entries, Categories=groups, Dependencies=edges)
    if deep:
        report['Coverage'] = dict(DirectoryTraversalTruncated=truncated, EntriesVisited=visited,
                                  FilesHashed=sum('SHA256' in item for item in entries),
                                  ArchiveMembersListed=MAX_MEMBERS - archive_budget['members'],
                                  ArchiveBytesCharged=MAX_EXPANDED_BYTES - archive_budget['bytes'])
        report['LaunchCandidates'] = [
            dict(Path=item['Path'], Admission=item['Status'],
                 DeclaredDLLs=launch_dependencies[item['Path']],
                 Blockers=item.get('Blockers', []),
                 RequiresReview=bool(item.get('ExtensionMismatch') or item.get('NameFindings') or
                                     item['Status'] != 'ADMISIBLE'))
            for item in entries if item['Category'] == 'EJECUTABLE']
        report['Review'] = [item['Path'] for item in entries if (
            item['Status'] in ('REVISION', 'BLOQUEADO') or item.get('ExtensionMismatch') or
            item.get('NameFindings') or item.get('Archive', {}).get('Status') == 'REVISION')]
        role_groups = defaultdict(list)
        for item in entries:
            role_groups[item['RoleHint']].append(item['Path'])
        report['RoleGroups'] = dict(sorted(role_groups.items()))
    if game is not None:
        report['Project'] = dict(
            Category='Game', Title=game, SuggestedDirectory=f'Game/{game}',
            CategoryEvidence='Declarada por el usuario.',
            DependencyFamilies=sorted({edge['Family'] for edge in edges if edge.get('Family')}),
            ExecutionEvidence='Inventario estatico. La ejecucion requiere una prueba del perfil SBEF.')
    return report
