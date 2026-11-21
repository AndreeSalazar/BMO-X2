"""Prepare FWSEC-FRTS data for the measured MSI GA106 VBIOS snapshot."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from .gsp_args import PAGE
from .gsp_wpr import MIB, WPR_BYTES, WPR_MAGIC


ROM_SHA256 = '3ea3feda53d5a8821c5a68fd1d44bf285100d65abe9661e3598bfd06fd804f61'
DESCRIPTOR = 0x41210
FWSEC_V3 = struct.Struct('<9IHBBHH')
RSA_BYTES = 384


def template(rom):
    if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
        raise ValueError('VBIOS distinta de la captura cotejada para 1462:397D')
    header, size, pkc, interface, imem_base, imem, entry, dmem_base, dmem, engine, code_id, count, versions, _ = (
        FWSEC_V3.unpack_from(rom,DESCRIPTOR))
    signature_start = DESCRIPTOR+FWSEC_V3.size
    ucode = DESCRIPTOR+(header>>16)
    if ((header>>8)&0xff!=3 or size!=imem+dmem or engine!=0x0400 or code_id!=9 or
            count!=versions.bit_count() or signature_start+count*RSA_BYTES>ucode or
            ucode+size>len(rom) or pkc+RSA_BYTES>dmem):
        raise ValueError('Descriptor FWSEC de produccion invalido')
    image = bytearray(rom[ucode:ucode+size])
    app = imem+interface
    version, header_bytes, stride, entries = struct.unpack_from('<4B',image,app)
    stop = app+header_bytes+stride*entries
    if version!=1 or header_bytes<4 or stride<8 or stop>len(image):
        raise ValueError('Interfaz DMEM de FWSEC invalida')
    mappers = [base for kind,base in (struct.unpack_from('<2I',image,pos)
               for pos in range(app+header_bytes,stop,stride)) if kind==4]
    if len(mappers)!=1 or mappers[0]+48>dmem:
        raise ValueError('Falta DMEMMAPPER de FWSEC')
    mapper = imem+mappers[0]
    command_offset, capacity = struct.unpack_from('<2I',image,mapper+8)
    if (capacity<44 or command_offset+capacity>dmem or
            command_offset<pkc+RSA_BYTES and pkc<command_offset+44):
        raise ValueError('El comando FRTS no cabe en DMEM')
    struct.pack_into('<11I',image,imem+command_offset,1,24,0,0,0,2,1,20,0,0,2)
    struct.pack_into('<I',image,mapper+44,0x15)
    signatures = rom[signature_start:signature_start+count*RSA_BYTES]
    return image,signatures,dict(
        imem_bytes=imem,imem_destination=imem_base,entry=entry,dmem_bytes=dmem,dmem_destination=dmem_base,
        signature_offset_in_dmem=pkc,signature_candidates=count,signature_bytes=RSA_BYTES,
        signature_versions=versions,signature_fuse_mmio=0x8241c0+(code_id-1)*4,
        frts_region_offset=imem+command_offset+32,physical_execution_verified=False)


def prepare(rom, metadata):
    if len(metadata)!=WPR_BYTES or struct.unpack_from('<2Q',metadata)!=(WPR_MAGIC,1) or any(metadata[200:]):
        raise ValueError('Se requiere WPR V1 nueva y sin respuesta de firmware')
    frts_start, frts_size, wpr_end, fb_size = struct.unpack_from('<4Q',metadata,152)
    if (fb_size!=12288*MIB or frts_size!=MIB or frts_start%PAGE or
            not fb_size-256*MIB<=frts_start<wpr_end<fb_size or frts_start+frts_size!=wpr_end):
        raise ValueError('Ventana FRTS fuera de la VRAM pre-limpiada de GA106')
    image, signatures, layout = template(rom)
    struct.pack_into('<2I',image,layout['frts_region_offset'],frts_start//PAGE,frts_size//PAGE)
    return bytes(image),signatures,dict(layout,frts_start=frts_start,frts_bytes=frts_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vbios',type=Path)
    parser.add_argument('wpr',type=Path)
    parser.add_argument('output',type=Path,help='New directory for ucode, candidate signatures and manifest')
    args = parser.parse_args()
    try:
        image,signatures,manifest = prepare(args.vbios.read_bytes(),args.wpr.read_bytes())
        args.output.mkdir()
        for filename,data in (('fwsec-frts.bin',image),('fwsec-signatures.bin',signatures)):
            (args.output/filename).write_bytes(data)
            manifest[filename] = hashlib.sha256(data).hexdigest()
        (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='ascii')
    except (OSError,ValueError) as error:
        parser.exit(1,f'FWSEC: {error}\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
