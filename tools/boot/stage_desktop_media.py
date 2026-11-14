"""Verify the desktop using a SBEF read from the boot volume by UEFI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid

from doom_fixture import desktop_gate_budget, make_packet, prepend_intro
from host.sbef.format import inspect
from scope import ROOT, workspace
from stage_bmo_x2 import bridge_variant
from wake import SPLASH_PROFILE, check, sha


def desktop_budget(image):
    report = inspect(image)
    layout = (
        ('0x40000000', 'RX', 8192),
        ('0x40003000', 'R', 4096),
        ('0x40004000', 'RW', 4096),
    )
    regions = report['Regions']
    if report['AbiVersion'] != 1 or len(image) > 16512 or len(regions) != len(layout):
        raise ValueError('El escritorio requiere SBEF ABI 1 y tres regiones de hasta 16512 bytes en archivo')
    for region, (address, permissions, limit) in zip(regions, layout, strict=True):
        if (region['Address'], region['Permissions']) != (address, permissions) or region['MappedBytes'] > limit:
            raise ValueError(f'La region de escritorio en {address} excede el perfil {permissions} de {limit} bytes')
        if permissions in ('RX', 'R') and not region['FileBytes']:
            raise ValueError(f'La region de escritorio en {address} requiere bytes de archivo')
    return dict(file_bytes=len(image), file_limit_bytes=16512,
                region_pages_bytes=sum(region['MappedBytes'] for region in regions),
                region_pages_limit_bytes=16384, stack_bytes=4096)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('abi_run', type=Path)
    parser.add_argument('splash_run', type=Path)
    parser.add_argument('desktop_run', type=Path)
    parser.add_argument('--cpu', choices=('qemu64', 'Nehalem'), default='qemu64')
    probes = parser.add_mutually_exclusive_group()
    probes.add_argument('--xhci-command', action='store_true', help='Run the QEMU-only xHCI command probe')
    probes.add_argument('--reuse-session', action='store_true', help='Run the QEMU-only desktop frame reuse probe')
    probes.add_argument('--ultra-j-view', type=Path, help='Test the ULTRA-J Ring 3 view SBEF in QEMU')
    parser.add_argument('--ultra-j-action', type=Path)
    parser.add_argument('--usb-desktop', type=Path, help='Desktop SBEF compiled with -UsbProbe')
    parser.add_argument('--usb-full-speed', action='store_true', help='Use USB 1.x in the xHCI probe')
    parser.add_argument('--usb-mouse', action='store_true', help='Probe a USB boot mouse instead of a keyboard')
    args = parser.parse_args()
    if bool(args.ultra_j_view) != bool(args.ultra_j_action):
        parser.error('--ultra-j-view y --ultra-j-action deben usarse juntos')
    abi, splash, desktop = map(workspace, (args.abi_run, args.splash_run, args.desktop_run))
    for path, profile in ((abi, 'ring0-abi-probe-0.1'), (splash, SPLASH_PROFILE),
                          (desktop, 'desktop-external')):
        if (path / 'profile.txt').read_text(encoding='utf-8-sig').strip() != profile:
            parser.error(f'Se requiere {profile}')
    check(abi)
    check(splash)
    if args.xhci_command != (args.usb_desktop is not None):
        parser.error('--xhci-command requiere --usb-desktop')
    if args.usb_full_speed and not args.xhci_command:
        parser.error('--usb-full-speed requiere --xhci-command')
    if args.usb_mouse and not args.xhci_command:
        parser.error('--usb-mouse requiere --xhci-command')
    usb_name = 'desktop-usb-mouse.sbef' if args.usb_mouse else 'desktop-usb-probe.sbef'
    if args.usb_desktop and args.usb_desktop.resolve() != (ROOT / 'build/desktop' / usb_name).resolve():
        parser.error('--usb-desktop requiere el resultado local de -UsbProbe')
    sbef = (args.usb_desktop or args.ultra_j_view or desktop / 'desktop.sbef').read_bytes()
    budget = desktop_budget(sbef)
    action = args.ultra_j_action.read_bytes() if args.ultra_j_action else b''
    if args.ultra_j_action:
        if not 9 <= len(action) <= 512:
            parser.error('ACTION.UJB debe ocupar de 9 a 512 bytes')
        if inspect(sbef)['Regions'][1]['MemoryBytes'] > 3576:
            parser.error('La vista ULTRA-J debe dejar 520 bytes de su pagina para ACTION.UJB')
    run = abi.parent / f'run-desktop-media-{uuid.uuid4().hex[:12]}'
    run.mkdir()
    scripts = Path(__file__).resolve().parent
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    kernel = ROOT / 'kernel'
    sources = ('boot/bridge/desktop_media_alloc.S', 'boot/bridge/desktop_media_read.S',
               'loader/external_sbef.S', 'syscalls/session_gate.S')
    for relative in sources:
        source = kernel / relative
        name = source.stem
        obj = run / f'{name}.o'
        flags = ['-DXHCI_COMMAND_PROBE'] if args.xhci_command else []
        if args.reuse_session:
            flags.append('-DDESKTOP_REUSE')
        if args.ultra_j_action:
            flags.append('-DULTRA_J_MEDIA')
        subprocess.run([llvm / 'clang.exe', '--target=x86_64-unknown-none-elf',
                        '-DDESKTOP_MEDIA', '-DDESKTOP_EXTERNAL', *flags,
                        '-c', source, '-o', obj], check=True)
        subprocess.run([llvm / 'llvm-objcopy.exe', '-O', 'binary', '--only-section=.text',
                        obj, run / f'{name}.bin'], check=True)
    obj = run / 'xhci-stage.o'
    flags = ['-DXHCI_COMMAND_PROBE'] if args.xhci_command else []
    if args.usb_mouse:
        flags.append('-DXHCI_MOUSE_PROBE')
    subprocess.run([llvm / 'clang.exe', '--target=x86_64-unknown-none-elf', '-x', 'assembler-with-cpp',
                    *flags, '-c', kernel / 'drivers/bus/xhci_inventory.inc', '-o', obj], check=True)
    subprocess.run([llvm / 'llvm-objcopy.exe', '-O', 'binary', '--only-section=.text',
                    obj, run / 'xhci-stage.bin'], check=True)

    reference = (abi / 'INICIO.X86').read_bytes()
    intro = (splash / 'INICIO.X86').read_bytes()
    gate = (run / 'session_gate.bin').read_bytes()
    gate_budget = desktop_gate_budget(gate)
    (run / 'session-gate.hex').write_text(
        '\n'.join(gate[index:index+16].hex(' ').upper() for index in range(0, len(gate), 16)) + '\n',
        encoding='ascii')
    loader = (run / 'external_sbef.bin').read_bytes()
    packet, _ = make_packet(reference, sbef, session_gate=gate, external=loader)
    if not (args.xhci_command or args.reuse_session):
        packet, _ = prepend_intro(packet, intro)
        (run / 'intro.x86').write_bytes(intro)
        shutil.copyfile(splash / 'source.casm', run / 'intro.casm')
    for name, content in (('reference.x86', reference), ('desktop.sbef', sbef), ('session-gate.bin', gate),
                          ('external-loader.bin', loader), ('INICIO.X86', packet), ('profile.txt', b'desktop-media\n')):
        (run / name).write_bytes(content)

    image = bridge_variant()
    reader = (run / 'desktop_media_read.bin').read_bytes()
    site, extension = 0x267, 0x3000
    if image[site:site+5] != bytes.fromhex('e894050000') or len(image) != extension or len(reader) > 4096:
        raise ValueError('El lector ya no cabe en el puente')
    struct.pack_into('<i', image, site+1, extension-site-5)
    extra = 0x2000
    for offset, old in ((0x5c, 0x2e00), (0x90, 0x4000), (0x150, 0x2e00), (0x158, 0x2e00)):
        if struct.unpack_from('<I', image, offset)[0] != old:
            raise ValueError('Cambio la cabecera PE del puente')
        struct.pack_into('<I', image, offset, old + extra)
    image.extend(reader.ljust(4096, b'\0'))
    driver = (run / 'xhci-stage.bin').read_bytes()
    if not 0 < len(driver) <= 4096:
        raise ValueError('La etapa xHCI no cabe en el puente EFI')
    image.extend(driver.ljust(4096, b'\0'))
    allocator = (run / 'desktop_media_alloc.bin').read_bytes()
    if image[0x400:0x404] != bytes.fromhex('4883ec28') or len(allocator) > 0xf0:
        raise ValueError('Cambio la reserva de memoria del puente')
    image[0x400:0x400+len(allocator)] = allocator
    base = run / 'build/Puente_Metal'
    efi, payload = base / 'EFI/BOOT/BOOTX64.EFI', base / 'METAL/INICIO.X86'
    for path, data in ((efi, image), (payload, packet)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shell = shutil.which('powershell.exe')
    subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    scripts / 'disk.ps1', '-OutputRoot', run, '-Programa', 'INICIO.X86', '-GPT'],
                   check=True, timeout=60)
    rejected = bytearray(sbef)
    struct.pack_into('<I', rejected, 116, 7)
    bad = run / 'rejected.sbef'
    bad.write_bytes(rejected)
    action_args = []
    if args.ultra_j_action:
        action_path = run / 'ACTION.UJB'
        action_path.write_bytes(action)
        action_args = ['--ultra-j-action', action_path]
    for case, path in (('external-permissions', bad), ('normal', run / 'desktop.sbef')):
        subprocess.run([sys.executable, '-B', scripts / 'prepare.py', '--workspace', run,
                        '--bmo-x2-folder', '--desktop', path, *action_args], check=True, timeout=30)
        if case != 'normal':
            (run / 'build/puente-normal.img').replace(run / 'build/puente-external-permissions.img')
    if args.xhci_command:
        (run / 'xhci-command.txt').write_text('QEMU\n', encoding='ascii')
    if args.usb_full_speed:
        (run / 'usb-full-speed.txt').write_text('QEMU\n', encoding='ascii')
    if args.usb_mouse:
        (run / 'usb-mouse.txt').write_text('QEMU\n', encoding='ascii')
    if args.reuse_session:
        (run / 'reuse-session.txt').write_text('QEMU\n', encoding='ascii')
    if args.ultra_j_view:
        (run / 'ultra-j-view.txt').write_text('QEMU\n', encoding='ascii')
    subprocess.run([sys.executable, '-B', scripts / 'probe.py', '--workspace', run, '--halt',
                    '--abi-probe', '--doom-fixture', '--ram-mib', '1024', '--cpu', args.cpu,
                    '--casos', 'normal', 'external-permissions'],
                   check=True, cwd=run, timeout=100)

    media = run / ('qemu-only' if args.xhci_command or args.reuse_session or args.ultra_j_view else 'media')
    files = {'EFI/BMO-X2/BMO-X2.EFI': efi, 'BMO-X2/INICIO.X86': payload,
             'BMO-X2/DESKTOP.SBF': run / 'desktop.sbef'}
    if args.ultra_j_action:
        files['BMO-X2/ACTION.UJB'] = action_path
    for name, src in files.items():
        target = media / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    report = json.loads((run / 'build/puente-test-results.json').read_text(encoding='utf-8'))
    cache = next(case['CpuL1'] for case in report['Cases'] if case['Case'] == 'normal')
    instructions = cache['Instruction'] or cache['Unified']
    gate_budget['FitsReportedL1Capacity'] = gate_budget['Bytes'] <= instructions['Bytes'] if instructions else None
    (run / 'profile.config').write_text(
        f'PROFILE_SCHEMA=1\nTARGET=x86_64\nPROFILE_SOURCE=QEMU_CPUID_BOOT_CPU\nQEMU_CPU={args.cpu}\n'
        f'CPU_CACHE_LEAF={cache["Leaf"] or "unknown"}\n'
        f'RING0_GATE_BYTES={gate_budget["Bytes"]}\nRING0_GATE_LIMIT_BYTES={gate_budget["LimitBytes"]}\n'
        f'RING0_GATE_SHA256={gate_budget["SHA256"]}\n'
        + ''.join(f'CPU_L1_{name.upper()}_BYTES={cache[name]["Bytes"] if cache[name] else "unknown"}\n'
                  for name in ('Instruction', 'Data', 'Unified')), encoding='ascii')
    report.update(run=run.name, evidence='QEMU', disk_sbef=True, physical_boot=False,
                  qemu_cpu=args.cpu,
                  desktop_reuse_probe=args.reuse_session,
                  ring0_gate_budget=gate_budget,
                  desktop_budget=budget, boot_packet_bytes=len(packet), uefi_bridge_bytes=len(image),
                  files={name: sha(media / name) for name in files})
    (run / 'qemu-run.json').write_text(json.dumps(dict(cpu=args.cpu, ram_mib=1024)) + '\n', encoding='ascii')
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(f'Media: {media}')


if __name__ == '__main__':
    main()
