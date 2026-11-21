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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bdf', type=bdf_arg, nargs='+')
    parser.add_argument('--ivrs', type=Path, help='Archivo IVRS. Por defecto consulta la tabla de Windows.')
    args = parser.parse_args()
    try:
        if args.ivrs:
            with args.ivrs.open('rb') as stream:
                data = stream.read(MAX_TABLE_BYTES + 1)
        else:
            data = windows_ivrs()
        report = inspect(data, args.bdf)
    except (OSError, ValueError) as error:
        parser.exit(1, f'IVRS: {error}\n')
    report['source'] = 'file' if args.ivrs else 'Windows GetSystemFirmwareTable'
    print(json.dumps(report, indent=2))
    return 0 if all(report['requesters'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
