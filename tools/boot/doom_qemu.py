"""Boot the DOOM arithmetic SBEF inside the single-page CASM ABI probe."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import uuid

from doom_fixture import make_packet, prepend_intro
from scope import ROOT, workspace
from wake import assemble, check

MINIMAL_SYSTEM_BUDGET = 2 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('sbef', type=Path)
    parser.add_argument('--intro', type=Path)
    parser.add_argument('--desktop-welcome', action='store_true', help='Verify Ring 0 cat, Ring 3 welcome and desktop')
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument('--desktop-present', type=Path)
    variants.add_argument('--session-gate', type=Path)
    parser.add_argument('--external-loader', type=Path)
    parser.add_argument('--reuse', nargs=2, type=Path, metavar=('STAGE', 'SECOND_SBEF'))
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument('--doom-external', action='store_true')
    profiles.add_argument('--doom-engine', action='store_true')
    profiles.add_argument('--desktop-doom', action='store_true')
    profiles.add_argument('--toolchain-client', choices=('gcc', 'clang', 'gcc-cpp', 'clang-cpp', 'rust', 'msvc', 'clang-cl'))
    profiles.add_argument('--rmlui-renderer', type=Path, help='Expected 16x16 Rust CPU raster probe, not a full RmlUi port')
    profiles.add_argument('--verrano-bsf', type=Path, help='Reference pixels for the CPL3 BSF reader probe')
    profiles.add_argument('--rmlui-native', type=Path, help='Symbol manifest for the real native UI engine profile')
    profiles.add_argument('--msvc-sections', type=Path, help='Symbol manifest for the three-region MSVC clock fixture')
    parser.add_argument('--wad', type=Path)
    parser.add_argument('--qemu', default='C:/Program Files/qemu/qemu-system-x86_64.exe')
    args = parser.parse_args()
    if args.desktop_welcome and not (args.intro and args.session_gate and args.external_loader):
        parser.error('La bienvenida requiere intro, sesion y cargador externo')
    raster_reference = args.rmlui_renderer or args.verrano_bsf
    if raster_reference and (not args.external_loader or not args.session_gate or args.intro):
        parser.error('La sonda Rust requiere cargador externo, puerta de sesion y no usa intro')
    if args.reuse and not args.toolchain_client:
        parser.error('--reuse requiere --toolchain-client')
    if args.toolchain_client and (args.session_gate or args.desktop_present or args.external_loader or args.intro):
        parser.error('El cliente ABI usa el paquete CASM embebido')
    engine = args.doom_engine or args.desktop_doom or bool(args.rmlui_native or args.msvc_sections or args.verrano_bsf)
    doom = args.doom_external or engine
    if doom and not (args.external_loader and args.session_gate):
        parser.error('DOOM externo requiere cargador y puerta de sesion')
    if args.wad and not doom:
        parser.error('El WAD requiere la sonda DOOM externa')
    if engine and not (args.wad or args.rmlui_native or args.msvc_sections or args.verrano_bsf):
        parser.error('El motor requiere el IWAD')
    if args.wad:
        with args.wad.open('rb') as stream:
            wad = stream.read(0x1000001)
        if not 12 <= len(wad) <= 0x1000000 or wad[:4] != b'IWAD':
            raise ValueError('Se requiere un IWAD de hasta 16 MiB')
    reference = workspace(args.reference)
    if (reference / 'profile.txt').read_text(encoding='utf-8-sig').strip() != 'ring0-abi-probe-0.1':
        raise ValueError('Se requiere un run CASM del perfil ABI')
    check(reference)
    base_packet = (reference / 'INICIO.X86').read_bytes()
    sbef = args.sbef.read_bytes()
    present = args.desktop_present.read_bytes() if args.desktop_present else None
    gate = args.session_gate.read_bytes() if args.session_gate else None
    external = args.external_loader.read_bytes() if args.external_loader else None
    reuse = tuple(path.read_bytes() for path in args.reuse) if args.reuse else None
    packet, _ = make_packet(base_packet, sbef, present, gate, external, engine=engine, reuse=reuse)
    if args.toolchain_client and len(packet) > MINIMAL_SYSTEM_BUDGET:
        raise ValueError(f'El paquete ABI ocupa {len(packet)} bytes y supera {MINIMAL_SYSTEM_BUDGET}')
    if args.intro:
        intro = workspace(args.intro)
        if (intro / 'profile.txt').read_text(encoding='utf-8-sig').strip() not in ('ring0-splash-hd-0.1', 'ring0-splash-0.1'):
            raise ValueError('Se requiere un run CASM del gato')
        check(intro)
        splash = (intro / 'INICIO.X86').read_bytes()
        packet, _ = prepend_intro(packet, splash)

    application = 'desktop' if (present is not None or gate is not None) and not doom else 'doom'
    if args.rmlui_native:
        application = 'rmlui'
    if args.msvc_sections:
        application = 'msvc-sections'
    if args.verrano_bsf:
        application = 'verrano'
    if args.toolchain_client:
        application = f'abi-{args.toolchain_client}'
    run = reference.parent / f'run-{application}-{uuid.uuid4().hex[:12]}'
    run.mkdir()
    if args.desktop_welcome:
        (run / 'welcome.txt').write_text('QEMU\n', encoding='ascii')
    if raster_reference:
        expected_pixels = raster_reference.read_bytes()
        if len(expected_pixels) != 16*16*4:
            raise ValueError('Referencia raster invalida')
        (run / 'raster-expected.bin').write_bytes(expected_pixels)
    if args.rmlui_native:
        shutil.copyfile(args.rmlui_native, run / 'ui-symbols.json')
    if args.msvc_sections:
        shutil.copyfile(args.msvc_sections, run / 'msvc-symbols.json')
    if args.wad:
        (run / 'wad-module.bin').write_bytes(struct.pack('<Q', len(wad)) + wad)
    (run / 'reference.x86').write_bytes(base_packet)
    (run / f'{application}.sbef').write_bytes(sbef)
    if reuse is not None:
        (run / 'abi-reuse.bin').write_bytes(reuse[0])
        (run / 'second.sbef').write_bytes(reuse[1])
    if present is not None:
        (run / 'desktop-present.bin').write_bytes(present)
    if gate is not None:
        (run / 'session-gate.bin').write_bytes(gate)
    if external is not None:
        (run / 'external-loader.bin').write_bytes(external)
        staging = struct.pack('<Q', len(sbef)) + sbef
        (run / 'sbef-module.bin').write_bytes(staging)
        rejected = bytearray(staging)
        count = struct.unpack_from('<H', sbef, 10)[0]
        struct.pack_into('<I', rejected, 8 + 52 + 32*(count-1), 7)
        (run / 'sbef-rejected.bin').write_bytes(rejected)
    if args.intro:
        (run / 'intro.x86').write_bytes(splash)
        shutil.copyfile(intro / 'source.casm', run / 'intro.casm')
    (run / 'INICIO.X86').write_bytes(packet)
    profile = 'desktop-external' if external is not None else 'desktop-session' if gate is not None else f'{application}-abi-fixture'
    if args.doom_external:
        profile = 'doom-external'
    if args.doom_engine:
        profile = 'doom-engine'
    if args.desktop_doom:
        profile = 'desktop-doom'
    if args.rmlui_renderer:
        profile = 'rmlui-raster-probe'
    if args.verrano_bsf:
        profile = 'verrano-bsf-probe'
    if args.rmlui_native:
        profile = 'rmlui-native'
    if args.msvc_sections:
        profile = 'msvc-sections'
    (run / 'profile.txt').write_text(f'{profile}\n', encoding='ascii')
    bridge = ROOT / 'kernel/boot/bridge'
    efi = run / 'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI'
    efi.parent.mkdir(parents=True)
    efi.write_bytes(assemble([bridge / name for name in ('cabecera.hex', 'entrada.hex', 'datos.hex', 'fuente.hex')]))
    disk_packet = run / 'build/Puente_Metal/METAL/INICIO.X86'
    disk_packet.parent.mkdir()
    disk_packet.write_bytes(packet)
    shell = shutil.which('powershell.exe')
    scripts = Path(__file__).resolve().parent
    subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(scripts / 'disk.ps1'),
                    '-OutputRoot', str(run), '-Programa', 'INICIO.X86', '-GPT'], check=True, timeout=60)
    subprocess.run([sys.executable, '-B', str(scripts / 'prepare.py'), '--workspace', str(run)],
                   check=True, timeout=30)
    qemu = str(Path(args.qemu).resolve())
    extra = ['--casos', 'normal', 'external-permissions'] if external is not None else []
    subprocess.run([sys.executable, '-B', str(scripts / 'probe.py'), '--workspace', str(run),
                    '--qemu', qemu, '--halt', '--abi-probe', '--doom-fixture', *extra],
                   check=True, cwd=run, timeout=100)
    report = json.loads((run / 'build/puente-test-results.json').read_text(encoding='utf-8'))
    if args.desktop_welcome:
        subprocess.run([sys.executable, '-B', str(scripts / 'probe.py'), '--workspace', str(run),
                        '--qemu', qemu, '--halt', '--abi-probe', '--doom-fixture', '--welcome-skip'],
                       check=True, cwd=run, timeout=100)
        skipped = json.loads((run / 'build/puente-test-results.json').read_text(encoding='utf-8'))
        for case in skipped['Cases']:
            case['Case'] = 'welcome-skip'
        report['Cases'].extend(skipped['Cases'])
        report['Total'] += skipped['Total']
        report['Passed'] += skipped['Passed']
    milestone = 'Rust desktop composition in CPL3' if present is not None else 'DoomGeneric fixed arithmetic in CPL3'
    if gate is not None:
        milestone = 'Interactive Rust desktop session in CPL3'
    if external is not None:
        milestone = 'External SBEF staged by QEMU and admitted in Ring 0'
    if args.doom_external:
        milestone = 'GCC DoomGeneric arithmetic and drawing from an external SBEF'
    if args.doom_engine:
        milestone = 'GCC DoomGeneric E1M1 and keyboard in CPL3 from an external SBEF'
    if args.msvc_sections:
        milestone = 'MSVC C++ PE32+ converted to SBEF uses the Rust session clock and stdout in CPL3'
    if args.desktop_doom:
        milestone = 'Rust desktop CABINA launches DoomGeneric E1M1 in CPL3'
    if args.rmlui_renderer:
        milestone = 'Shared no_std Rust CPU rasterizer executes in CPL3; full RmlUi engine remains HOST'
    if args.verrano_bsf:
        milestone = 'VERRANO checks the original BSF1 container in CPL3 with a software reference backend'
    if args.rmlui_native:
        milestone = 'Native RmlUi/FreeType C++ engine and Rust CPU drawing, with ULTRA-J action in CPL3'
    if args.desktop_welcome:
        milestone = 'Ring 0 cat, admitted Ring 3 welcome, then desktop; skip preserves first input'
    if args.toolchain_client:
        milestone = f'{args.toolchain_client.upper()} client exercises the CASM ABI in CPL3'
        report['toolchain'] = args.toolchain_client
        second_bytes = len(reuse[1]) if reuse is not None else 0
        report['minimal_system_budget'] = dict(
            limit_bytes=MINIMAL_SYSTEM_BUDGET,
            packet_bytes=len(packet),
            packet_header_bytes=24,
            embedded_sbef_bytes=len(sbef) + second_bytes,
            ring0_body_bytes=len(packet) - len(sbef) - second_bytes - 24,
            packet_headroom_bytes=MINIMAL_SYSTEM_BUDGET - len(packet),
            uefi_bridge_bytes=efi.stat().st_size,
            packet_and_bridge_bytes=len(packet) + efi.stat().st_size,
            guest_ram_mib=256,
        )
        if reuse is not None:
            report['second_sbef_sha256'] = hashlib.sha256(reuse[1]).hexdigest()
    report.update(run=run.name, evidence='QEMU', milestone=f'Cat intro then {milestone}' if args.intro else milestone)
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    (run / 'qemu-run.json').write_text(json.dumps(dict(cpu='qemu64', ram_mib=256)) + '\n', encoding='ascii')
    print(f'Run: {run}')


if __name__ == '__main__':
    main()
