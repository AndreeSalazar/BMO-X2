"""Inventario HOST de AMD-Vi para los BDF indicados. Solo lectura."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


MAX_TABLE_BYTES = 1 << 20
IVHD_HEADERS = {0x10: 24, 0x11: 40, 0x40: 40}


def bdf_arg(text):
    fields = re.fullmatch(r'([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([01][0-9a-fA-F])\.([0-7])', text)
    if not fields:
        raise argparse.ArgumentTypeError('Se requiere un BDF ssss:bb:dd.f')
    segment, bus, slot, function = (int(field, 16) for field in fields.groups())
    return segment, bus << 8 | slot << 3 | function


def bdf_text(segment, requester):
    return f'{segment:04x}:{requester >> 8:02x}:{(requester >> 3) & 31:02x}.{requester & 7}'


def windows_ivrs():
    import ctypes
    import sys

    if sys.platform != 'win32':
        raise ValueError('Use --ivrs con una copia de la tabla ACPI IVRS')
    read_table = ctypes.WinDLL('kernel32', use_last_error=True).GetSystemFirmwareTable
    read_table.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
    read_table.restype = ctypes.c_uint32
    provider = int.from_bytes(b'ACPI', 'big')
    table_id = int.from_bytes(b'IVRS', 'little')
    size = read_table(provider, table_id, None, 0)
    if not size:
        raise OSError(f'Windows no entrego IVRS (error {ctypes.get_last_error()})')
    if not 48 <= size <= MAX_TABLE_BYTES:
        raise ValueError('Longitud IVRS fuera de limite')
    output = ctypes.create_string_buffer(size)
    if read_table(provider, table_id, output, size) != size:
        raise OSError('La lectura completa de IVRS no coincide con su longitud')
    return output.raw


def scopes(block, header_size):
    offset = header_size
    pending = None
    result = []
    while offset < len(block):
        kind = block[offset]
        if kind == 0xf0 and block[0] == 0x40 and len(block) - offset >= 22:
            size = 22 + block[offset + 21]
        elif kind < 0x80:
            size = 4 << (kind >> 6)
        else:
            raise ValueError(f'Tipo de entrada IVHD no admitido: {kind:#04x}')
        if size > len(block) - offset:
            raise ValueError('Entrada IVHD truncada')
        requester = struct.unpack_from('<H', block, offset + 1)[0]
        alias = struct.unpack_from('<H', block, offset + 5)[0] if kind in (0x42, 0x43) else None
        if kind == 1:
            result.append((0, 0xffff, None))
        elif kind in (2, 0x42, 0x46):
            result.append((requester, requester, alias))
        elif kind in (3, 0x43, 0x47):
            if pending is not None:
                raise ValueError('Rango IVHD anidado')
            pending = requester, alias
        elif kind == 4:
            if pending is None or requester < pending[0]:
                raise ValueError('Fin de rango IVHD invalido')
            result.append((pending[0], requester, pending[1]))
            pending = None
        offset += size
    if pending is not None:
        raise ValueError('Rango IVHD sin fin')
    return result


def device_table_requirements(units):
    requirements = []
    for (segment, requester), (kind, _flags, _capability, _mmio, scope) in sorted(units.items()):
        if not scope:
            continue
        first = min(item[0] for item in scope)
        scope_last = max(last for _, last, _ in scope)
        highest = max(max(last, alias if alias is not None else last) for _, last, alias in scope)
        entries = highest + 1
        raw_bytes = entries * 32
        pages = (raw_bytes + 4095) // 4096
        requirements.append({
            'unit_bdf': bdf_text(segment, requester),
            'ivhd_type': f'{kind:02x}',
            'scope_first': bdf_text(segment, first),
            'scope_last': bdf_text(segment, scope_last),
            'scope_ranges': [
                {
                    'first': bdf_text(segment, range_first),
                    'last': bdf_text(segment, range_last),
                    'alias': None if alias is None else f'{alias:04x}',
                }
                for range_first, range_last, alias in scope
            ],
            'highest_device_id': f'{highest:04x}',
            'minimum_entries': entries,
            'minimum_bytes': raw_bytes,
            'minimum_4k_pages': pages,
            'minimum_aligned_bytes': pages * 4096,
            'layout': 'contiguous without DTE segmentation',
        })
    return requirements


def inspect(data, requested):
    if not 48 <= len(data) <= MAX_TABLE_BYTES or data[:4] != b'IVRS':
        raise ValueError('Cabecera ACPI IVRS invalida')
    if struct.unpack_from('<I', data, 4)[0] != len(data) or sum(data) & 0xff:
        raise ValueError('Longitud o checksum de IVRS invalido')

    units = {}
    blocks = []
    offset = 48
    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError('Bloque IVRS truncado')
        kind, flags, size = struct.unpack_from('<BBH', data, offset)
        if not 6 <= size <= len(data) - offset:
            raise ValueError('Longitud de bloque IVRS invalida')
        block = data[offset:offset + size]
        blocks.append(f'{kind:02x}')
        offset += size
        if kind not in IVHD_HEADERS:
            continue
        header_size = IVHD_HEADERS[kind]
        if len(block) < header_size:
            raise ValueError('Cabecera IVHD truncada')
        requester, capability, mmio, segment = struct.unpack_from('<HHQH', block, 4)
        if mmio == 0 or mmio & 0x3fff:
            raise ValueError('Base MMIO IVHD invalida')
        scope = scopes(block, header_size)
        key = segment, requester
        if key in units and kind == units[key][0]:
            raise ValueError('IVHD duplicado para la misma unidad')
        if key not in units or kind > units[key][0]:
            units[key] = kind, flags, capability, mmio, scope

    targets = {}
    for segment, requester in requested:
        matches = []
        for (unit_segment, unit_requester), (kind, flags, capability, mmio, scope) in units.items():
            if segment != unit_segment:
                continue
            for first, last, alias in scope:
                if first <= requester <= last:
                    matches.append({
                        'unit_bdf': bdf_text(segment, unit_requester),
                        'ivhd_type': f'{kind:02x}',
                        'ivhd_flags': f'{flags:02x}',
                        'pci_capability_offset': f'{capability:#x}',
                        'mmio_base': f'{mmio:#018x}',
                        'range_first': bdf_text(segment, first),
                        'range_last': bdf_text(segment, last),
                        'alias': None if alias is None else bdf_text(segment, alias),
                    })
        targets[bdf_text(segment, requester)] = matches
    return dict(schema=1, evidence='HOST: ACPI firmware inventory', table_bytes=len(data),
                table_revision=data[8], table_sha256=hashlib.sha256(data).hexdigest(),
                block_types=blocks, requesters=targets,
                device_table_requirements=device_table_requirements(units),
                bmo_x2_dma_isolation_verified=False)


def reconcile_census(report, census, census_sha256=None):
    """Coteja los solicitantes observados; no asigna dominios ni activa DMA."""
    active = {}
    for device in census.get('bus_master_enabled', []):
        bdf = device.get('bdf')
        if not isinstance(bdf, str):
            raise ValueError('Solicitante activo sin BDF valido en el censo')
        try:
            bdf_arg(bdf)
        except argparse.ArgumentTypeError as error:
            raise ValueError(f'BDF invalido en el censo: {bdf}') from error
        if bdf in active:
            raise ValueError(f'Solicitante bus-master duplicado: {bdf}')
        command = device.get('pci_command')
        if not isinstance(command, str) or not re.fullmatch(r'[0-9a-fA-F]{4}', command):
            raise ValueError(f'PCI Command invalido para {bdf}')
        if not int(command, 16) & 0x0004:
            raise ValueError(f'{bdf} figura como activo pero PCI Command no tiene Bus Master')
        active[bdf] = device

    known = dict(active)
    for device in census.get('physical_device_hints', []):
        bdf = device.get('bdf')
        if not isinstance(bdf, str):
            raise ValueError('Dato auxiliar de dispositivo sin BDF valido')
        try:
            bdf_arg(bdf)
        except argparse.ArgumentTypeError as error:
            raise ValueError(f'BDF auxiliar invalido: {bdf}') from error
        command = device.get('pci_command')
        if not isinstance(command, str) or not re.fullmatch(r'[0-9a-fA-F]{4}', command):
            raise ValueError(f'PCI Command auxiliar invalido para {bdf}')
        if bdf in known and known[bdf] != device:
            raise ValueError(f'Datos auxiliares contradicen el censo para {bdf}')
        known[bdf] = device

    observed = set(known)
    for bdf in census.get('ivrs_requesters', []):
        if not isinstance(bdf, str):
            raise ValueError('Lista IVRS contiene un BDF no textual')
        try:
            bdf_arg(bdf)
        except argparse.ArgumentTypeError as error:
            raise ValueError(f'BDF IVRS invalido en el censo: {bdf}') from error
        observed.add(bdf)

    rows = []
    uncovered = []
    for bdf in sorted(observed):
        device = known.get(bdf)
        matches = report['requesters'].get(bdf, [])
        if not matches:
            uncovered.append(bdf)
        command = None if device is None else device['pci_command'].lower()
        rows.append({
            'bdf': bdf,
            'vendor_device': None if device is None else device.get('id'),
            'pci_class': None if device is None else device.get('pci_class'),
            'pci_command': command,
            'bus_master_enabled': None if command is None else bool(int(command, 16) & 0x0004),
            'device_evidence': None if device is None else device.get('evidence'),
            'ivrs_scope_matches': len(matches),
            'ivrs_unit': None if not matches else matches[0]['unit_bdf'],
            'ivrs_alias': None if not matches else matches[0]['alias'],
            'scope_covered': bool(matches),
            'scope_unambiguous': len(matches) == 1,
            'domain_assignment_verified': False,
        })

    active_count = sum(1 for row in rows if row['bus_master_enabled'])
    ambiguous = [row['bdf'] for row in rows if row['ivrs_scope_matches'] > 1]
    return {
        'evidence': 'HOST static join of the captured PCI census and ACPI IVRS scopes',
        'census_sha256': census_sha256,
        'ivrs_sha256': report['table_sha256'],
        'observed_requesters': len(rows),
        'bus_master_enabled': active_count,
        'scope_covered': len(rows) - len(uncovered),
        'uncovered_requesters': uncovered,
        'ambiguous_requesters': ambiguous,
        'all_observed_requesters_in_ivrs_scope': not uncovered,
        'all_observed_requesters_unambiguous': not ambiguous,
        'all_domains_verified': False,
        'physical_translation_permitted': False,
        'reason': 'IVRS scope coverage is not proof of DTE programming, quiescence, invalidation, or a bounded DMA domain.',
        'requesters': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bdf', type=bdf_arg, nargs='*')
    parser.add_argument('--ivrs', type=Path, help='Archivo IVRS. Por defecto consulta la tabla de Windows.')
    parser.add_argument('--census-json', type=Path, help='Censo PCI METAL; solo lectura, no habilita AMD-Vi.')
    parser.add_argument('--output-json', type=Path, help='Guarda el inventario HOST resultante en JSON.')
    args = parser.parse_args()
    try:
        census = None
        census_sha256 = None
        requested = list(args.bdf)
        if args.census_json:
            census_bytes = args.census_json.read_bytes()
            if len(census_bytes) > MAX_TABLE_BYTES * 4:
                raise ValueError('Censo PCI fuera de limite')
            census = json.loads(census_bytes)
            census_sha256 = hashlib.sha256(census_bytes).hexdigest()
            requested.extend(bdf_arg(item) for item in census.get('ivrs_requesters', []))
            requested.extend(bdf_arg(item['bdf']) for item in census.get('bus_master_enabled', []))
        if not requested:
            parser.error('Indique uno o mas BDF o --census-json')
        requested = sorted(set(requested))
        if args.ivrs:
            with args.ivrs.open('rb') as stream:
                data = stream.read(MAX_TABLE_BYTES + 1)
        else:
            data = windows_ivrs()
        report = inspect(data, requested)
        if census is not None:
            report['physical_dma_preflight'] = reconcile_census(report, census, census_sha256)
    except (OSError, ValueError) as error:
        parser.exit(1, f'IVRS: {error}\n')
    report['source'] = 'file' if args.ivrs else 'Windows GetSystemFirmwareTable'
    report['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output = json.dumps(report, indent=2)
    if args.output_json:
        args.output_json.write_text(output + '\n', encoding='ascii')
    print(output)
    scope_ok = all(report['requesters'].values())
    if census is not None:
        audit = report['physical_dma_preflight']
        scope_ok = scope_ok and not audit['uncovered_requesters'] and not audit['ambiguous_requesters']
    return 0 if scope_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
