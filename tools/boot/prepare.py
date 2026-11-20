"""Instala archivos del puente en una copia de nuestro disco FAT32 virtual.

Solo acepta archivos .img bajo build/. Nunca abre dispositivos fisicos.
"""
import argparse
from pathlib import Path
import shutil
import struct
import uuid
import zlib
from scope import workspace
from sbef_probe_cases import MUTATIONS, mutated_packet

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace',required=True,type=Path)
parser.add_argument('--caso', choices=['normal', 'firma', 'suma', 'ausente', 'excesivo', 'entrada', 'salida', 'contexto', *MUTATIONS], default='normal')
parser.add_argument('--profile',choices=['hello','flappy-preview'],default='hello')
parser.add_argument('--bmo-x2-folder', action='store_true', help='Use a separate payload folder in the virtual image')
parser.add_argument('--desktop', type=Path, help='Add the desktop SBEF to the BMO-X2 folder')
parser.add_argument('--native-ui',action='store_true',help='Explicit large UI profile in BMO-X2/DESKTOP')
parser.add_argument('--nvidia-probe', action='store_true', help='Place the native UI candidate in BMO-X2/GPU')
parser.add_argument('--ultra-j-action', type=Path, help='Add ACTION.UJB alongside the desktop SBEF')
args = parser.parse_args()
if args.bmo_x2_folder and (args.profile != 'hello' or args.caso != 'normal'):
    parser.error('--bmo-x2-folder requires the normal bridge case')
if args.desktop and not args.bmo_x2_folder:
    parser.error('--desktop requires --bmo-x2-folder')
if args.native_ui and not args.desktop:parser.error('--native-ui requires --desktop')
if args.nvidia_probe and not args.native_ui:parser.error('--nvidia-probe requires --native-ui')
if args.ultra_j_action and not args.desktop:
    parser.error('--ultra-j-action requires --desktop')
root = workspace(args.workspace)
build = root / 'build'
if args.profile=='flappy-preview' and args.caso!='normal':raise ValueError('Visual preview uses only the normal virtual image case')
source = build / 'disco-fat32-gpt.img'
output = build / f'puente-{args.caso}.img'
if not source.resolve().is_relative_to(build.resolve()) or not output.resolve().is_relative_to(build.resolve()):
    raise ValueError('Las imagenes deben estar dentro de build/')
shutil.copyfile(source, output)
efi = (build / ('Flappy_Metal/PC_PREVIEW/EFI/ORQUESTADOR/FLAPPY.EFI' if args.profile=='flappy-preview' else 'Puente_Metal/EFI/BOOT/BOOTX64.EFI')).read_bytes()
if args.caso == 'salida':
    # Solo la copia de prueba: MapKey cero para provocar INVALID_PARAMETER.
    if efi[0xc90:0xc94] != bytes.fromhex('488b5558'):
        raise ValueError('Cambio el contrato de la inyeccion MapKey')
    efi = efi[:0xc90] + bytes.fromhex('31d29090') + efi[0xc94:]
if args.caso == 'contexto':
    # Solo la copia QEMU. Mantener RBP y entregar RDI=0 al payload.
    if efi[0xe4a:0xe50] != bytes.fromhex('48 89 EF FF 55 70'):
        raise ValueError('Cambio el punto de entrega RDI')
    efi = efi[:0xe4a] + bytes.fromhex('31 FF 90') + efi[0xe4d:]

with output.open('r+b') as disk:
    def read(offset, size):
        disk.seek(offset)
        data = disk.read(size)
        if len(data) != size:
            raise ValueError('Imagen truncada')
        return data

    def write(offset, data):
        if offset < 0 or offset + len(data) > output.stat().st_size:
            raise ValueError('Escritura fuera de la imagen virtual')
        disk.seek(offset)
        disk.write(data)

    primary = bytearray(read(512, 512))
    if primary[:8] != b'EFI PART':
        raise ValueError('La referencia debe ser GPT')
    table_lba = struct.unpack_from('<Q', primary, 72)[0]
    table_count, table_stride = struct.unpack_from('<II', primary, 80)
    if (table_count, table_stride) != (128, 128):
        raise ValueError('Geometria GPT de referencia inesperada')
    table = bytearray(read(table_lba * 512, table_count * table_stride))
    volume_lba = struct.unpack_from('<Q', table, 32)[0]
    bpb = read(volume_lba * 512, 512)
    if bpb[510:] != b'\x55\xaa' or struct.unpack_from('<H', bpb, 11)[0] != 512:
        raise ValueError('Volumen FAT32 de referencia invalido')
    spc, reserved, fat_count = bpb[13], struct.unpack_from('<H', bpb, 14)[0], bpb[16]
    fat_sectors, root_cluster = struct.unpack_from('<I', bpb, 36)[0], struct.unpack_from('<I', bpb, 44)[0]
    if spc not in (1, 2, 4, 8, 16, 32, 64) or fat_count != 2:
        raise ValueError('Geometria FAT32 inesperada')
    cluster_bytes = 512 * spc
    fat_offset = (volume_lba + reserved) * 512
    fat = bytearray(read(fat_offset, fat_sectors * 512))
    data_offset = (volume_lba + reserved + fat_count * fat_sectors) * 512
    cluster_count = (output.stat().st_size - data_offset) // cluster_bytes

    def cluster_offset(cluster):
        if not 2 <= cluster < cluster_count + 2:
            raise ValueError('Cluster fuera de imagen')
        return data_offset + (cluster - 2) * cluster_bytes

    def allocate(count):
        chain = []
        for cluster in range(2, min(len(fat) // 4, cluster_count + 2)):
            if struct.unpack_from('<I', fat, cluster * 4)[0] == 0:
                chain.append(cluster)
                if len(chain) == count:
                    break
        if len(chain) != count:
            raise ValueError('Sin espacio en la imagen virtual')
        for n, cluster in enumerate(chain):
            struct.pack_into('<I', fat, cluster * 4, chain[n + 1] if n + 1 < count else 0x0fffffff)
        return chain

    def entry(name, attr, cluster, size=0):
        record = bytearray(32)
        record[:11] = name
        record[11] = attr
        struct.pack_into('<H', record, 20, cluster >> 16)
        struct.pack_into('<H', record, 26, cluster & 65535)
        struct.pack_into('<I', record, 28, size)
        return record

    root_data = bytearray(read(cluster_offset(root_cluster), cluster_bytes))
    metal = next(root_data[p:p + 32] for p in range(0, cluster_bytes, 32) if root_data[p:p + 11] == b'METAL      ')
    if args.bmo_x2_folder:
        folder = root_data.index(metal)
        root_data[folder:folder + 11] = b'BMO-X2     '
    metal_cluster = (struct.unpack_from('<H', metal, 20)[0] << 16) | struct.unpack_from('<H', metal, 26)[0]
    metal_offset = cluster_offset(metal_cluster)
    directory = bytearray(read(metal_offset, cluster_bytes))
    if args.native_ui:
        child,=allocate(1)
        parent=bytearray(cluster_bytes)
        parent[:32]=entry(b'.          ',0x10,metal_cluster)
        parent[32:64]=entry(b'..         ',0x10,root_cluster)
        name = b'GPU        ' if args.nvidia_probe else b'DESKTOP    '
        parent[64:96]=entry(name,0x10,child)
        write(metal_offset,parent)
        old=directory;directory=bytearray(cluster_bytes)
        directory[:32]=entry(b'.          ',0x10,child)
        directory[32:64]=entry(b'..         ',0x10,metal_cluster)
        cursor=64
        for i in range(0,cluster_bytes,32):
            record=old[i:i+32]
            if record[0] not in (0,0xe5,ord('.')):
                directory[cursor:cursor+32]=record;cursor+=32
        metal_cluster=child;metal_offset=cluster_offset(child)
    packet_pos = next(p for p in range(0, cluster_bytes, 32) if directory[p:p + 11] == b'INICIO  X86')
    if args.profile=='flappy-preview':directory[packet_pos:packet_pos+11]=b'FLAPPY  X86'
    packet_cluster = (struct.unpack_from('<H', directory, packet_pos + 20)[0] << 16) | struct.unpack_from('<H', directory, packet_pos + 26)[0]
    packet_offset = cluster_offset(packet_cluster)
    if args.caso == 'ausente':
        directory[packet_pos] = 0xe5
    elif args.caso in ('firma', 'suma', 'entrada'):
        delta = {'firma': 0, 'suma': 24, 'entrada': 12}[args.caso]
        changed = bytearray(read(packet_offset, cluster_bytes))
        changed[delta] ^= 0x80
        write(packet_offset, changed)
    elif args.caso in MUTATIONS:
        packet = mutated_packet((build/'Puente_Metal/METAL/INICIO.X86').read_bytes(), args.caso)
        if struct.unpack_from('<I', directory, packet_pos + 28)[0] != len(packet):
            raise ValueError('ABI-PROBE: tamano FAT32 del paquete distinto')
        cluster = packet_cluster
        seen = set()
        for start in range(0, len(packet), cluster_bytes):
            if cluster in seen:
                raise ValueError('ABI-PROBE: cadena FAT32 ciclica')
            seen.add(cluster)
            write(cluster_offset(cluster), packet[start:start+cluster_bytes])
            cluster = struct.unpack_from('<I', fat, cluster * 4)[0] & 0x0fffffff
        if cluster < 0x0ffffff8:
            raise ValueError('ABI-PROBE: cadena FAT32 excede el paquete')
    elif args.caso == 'excesivo':
        oversized = (build / 'Puente_Metal/METAL/INICIO.X86').read_bytes().ljust(4097, b'\0')
        chain = allocate((len(oversized) + cluster_bytes - 1) // cluster_bytes)
        for n, cluster in enumerate(chain):
            write(cluster_offset(cluster), oversized[n * cluster_bytes:(n + 1) * cluster_bytes].ljust(cluster_bytes, b'\0'))
        directory[packet_pos:packet_pos + 32] = entry(b'INICIO  X86', 0x20, chain[0], len(oversized))
    if args.desktop:
        desktop = args.desktop.read_bytes()
        if not 64 <= len(desktop) <= (2*1024*1024 if args.native_ui else 16512):
            raise ValueError('Tamano invalido del SBEF de escritorio')
        desktop_chain = allocate((len(desktop) + cluster_bytes - 1) // cluster_bytes)
        for n, cluster in enumerate(desktop_chain):
            data = desktop[n * cluster_bytes:(n + 1) * cluster_bytes]
            write(cluster_offset(cluster), data.ljust(cluster_bytes, b'\0'))
        slot = next(i for i in range(0, len(directory), 32) if directory[i] == 0)
        directory[slot:slot+32] = entry(b'DESKTOP SBF', 0x20, desktop_chain[0], len(desktop))
    if args.ultra_j_action:
        action = args.ultra_j_action.read_bytes()
        if not 9 <= len(action) <= min(512, cluster_bytes):
            raise ValueError('Tamano invalido de ACTION.UJB')
        action_cluster, = allocate(1)
        write(cluster_offset(action_cluster), action.ljust(cluster_bytes, b'\0'))
        slot = next(i for i in range(0, len(directory), 32) if directory[i] == 0)
        directory[slot:slot+32] = entry(b'ACTION  UJB', 0x20, action_cluster, len(action))
    write(metal_offset, directory)

    efi_dir, boot_dir = allocate(2)
    chain = allocate((len(efi) + cluster_bytes - 1) // cluster_bytes)
    for n, cluster in enumerate(chain):
        write(cluster_offset(cluster), efi[n * cluster_bytes:(n + 1) * cluster_bytes].ljust(cluster_bytes, b'\0'))
    for cluster, parent, child in ((efi_dir, root_cluster, entry(b'BOOT       ', 0x10, boot_dir)),
                                    (boot_dir, efi_dir, entry(b'BOOTX64 EFI', 0x20, chain[0], len(efi)))):
        block = bytearray(cluster_bytes)
        block[:32] = entry(b'.          ', 0x10, cluster)
        block[32:64] = entry(b'..         ', 0x10, parent)
        block[64:96] = child
        write(cluster_offset(cluster), block)
    free = next(p for p in range(0, cluster_bytes, 32) if root_data[p] in (0, 0xe5))
    root_data[free:free + 32] = entry(b'EFI        ', 0x10, efi_dir)
    write(cluster_offset(root_cluster), root_data)
    for n in range(fat_count):
        write(fat_offset + n * len(fat), fat)
    # La misma particion pasa a tipo ESP; mantener ambas tablas/cabeceras GPT.
    table[:16] = uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b').bytes_le
    for header_lba in (1, struct.unpack_from('<Q', primary, 32)[0]):
        header = bytearray(read(header_lba * 512, 512))
        table_at = struct.unpack_from('<Q', header, 72)[0]
        write(table_at * 512, table)
        struct.pack_into('<I', header, 88, zlib.crc32(table))
        struct.pack_into('<I', header, 16, 0)
        struct.pack_into('<I', header, 16, zlib.crc32(header[:92]))
        write(header_lba * 512, header)
print(f'OK: {output.name}: ESP FAT32 con BOOTX64.EFI y paquete externo; caso {args.caso}.')
