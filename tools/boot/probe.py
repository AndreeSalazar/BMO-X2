"""Prueba real del puente bajo OVMF/QEMU usando QMP por tuberias, sin puertos TCP."""
import argparse
import hashlib
import json
import msvcrt
from pathlib import Path
import queue
import re
import shutil
import socket
import struct
import subprocess
import threading
import time
import sys
from scope import workspace
from cpu_config import identify, register
from splash_capture import compare_frame
from fault_capture import fault_evidence
from memory_capture import memory_evidence
from paging_capture import paging_evidence
from user_fault_capture import user_fault_evidence
from sbef_probe_cases import MUTATIONS, SBEF_OFFSET, mutated_packet

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace',required=True,type=Path)
parser.add_argument('--casos', nargs='+', choices=['normal','firma','suma','entrada','ausente','excesivo','salida','contexto','external-permissions','amdvi-missing', *MUTATIONS], default=['normal'])
parser.add_argument('--qemu', default='C:/Program Files/qemu/qemu-system-x86_64.exe')
parser.add_argument('--cpu', choices=['qemu64', 'Nehalem'], default='qemu64')
parser.add_argument('--ram-mib', type=int, choices=[256,1024], default=256)
parser.add_argument('--halt',action='store_true',help='Expect the own terminal instead of a payload return')
parser.add_argument('--identify',action='store_true',help='Collect CPUID leaf 0 at the terminal')
parser.add_argument('--stack',action='store_true',help='Check the selected stack and handoff status')
parser.add_argument('--fault',action='store_true',help='Check the own #UD gate and exception frame')
parser.add_argument('--memory', action='store_true', help='Check the conventional memory frame')
parser.add_argument('--frame-cycle', action='store_true', help='Check ownership, release and scrub of a physical frame')
parser.add_argument('--paging', action='store_true', help='Check the active page tables and read-only NX alias')
parser.add_argument('--user-fault', action='store_true', help='Check CPL3 page fault and cleanup')
parser.add_argument('--abi-probe', action='store_true', help='Check embedded SBEF and the SYSCALL prototype')
parser.add_argument('--doom-fixture', action='store_true', help='Verify the run-specific DOOM ABI fixture')
parser.add_argument('--welcome-skip', action='store_true', help='Skip the explicit Ring 3 welcome fixture with F2')
parser.add_argument('--hot-unmap', action='store_true', help='Check live revocation and the fault journal')
parser.add_argument('--splash',action='store_true',help='Capture the three logo frames')
parser.add_argument('--splash-hd',action='store_true',help='Use the 64-cell logo layout')
args = parser.parse_args()
if args.welcome_skip and not (args.doom_fixture and (workspace(args.workspace) / 'welcome.txt').is_file()):
    parser.error('--welcome-skip requiere el perfil de bienvenida')
if not args.abi_probe and set(args.casos).intersection(MUTATIONS):
    parser.error('SBEF mutation cases require the ABI probe')
memory_case = args.memory or args.frame_cycle or args.paging
user_case = args.user_fault or args.abi_probe or args.hot_unmap
if any((args.identify,args.stack,args.splash,args.fault,memory_case,user_case)) and not args.halt:
    parser.error('The selected probe requires --halt')
if (args.splash_hd and not args.splash) or ('contexto' in args.casos and not (args.stack or args.fault or memory_case or user_case)) or sum((args.identify,args.stack,args.splash,args.fault,args.memory,args.frame_cycle,args.paging,args.user_fault,args.abi_probe,args.hot_unmap)) > 1 or ((memory_case or user_case) and args.ram_mib != 256 and not args.doom_fixture):
    parser.error('Invalid combination of payload and probe cases')
ROOT = workspace(args.workspace)
nvidia_gsp_sample = args.doom_fixture and (ROOT / 'nvidia-gsp-sample.txt').is_file()
nvidia_gsp_stage = nvidia_gsp_sample and (ROOT / 'nvidia-gsp-stage.json').is_file()
amdvi_post = args.doom_fixture and (ROOT / 'amdvi-post-probe.txt').is_file()
amdvi_coexist = amdvi_post and (ROOT / 'amdvi-coexist-probe.txt').is_file()
amdvi_storage = amdvi_coexist and (ROOT / 'amdvi-storage.txt').is_file()
amdvi_routed = amdvi_storage and (ROOT / 'amdvi-routed.txt').is_file()
amdvi_nvme = amdvi_storage and (ROOT / 'amdvi-nvme.txt').is_file()
dma_census = amdvi_post and (ROOT / 'dma-census-probe.txt').is_file()
storage_state = dma_census and (ROOT / 'storage-state.txt').is_file()
full_hd = storage_state and (ROOT / 'full-hd.txt').is_file()
full_hd_native = full_hd and (ROOT / 'full-hd.txt').read_text(encoding='ascii').strip() == 'cpu-gop-native-1920x1080'
desktop_cases = ['normal', 'external-permissions']
if args.doom_fixture and (not args.abi_probe or args.casos not in
                          (['normal'], desktop_cases, desktop_cases + (['amdvi-missing'] if amdvi_post else []))):
    parser.error('DOOM requires the normal ABI probe case')
if 'amdvi-missing' in args.casos and not amdvi_post:
    parser.error('The missing AMD-Vi case requires the post-EBS profile')
doom = None
intro_size = 0
intro_rows = None
external = None
desktop_media = desktop_doom = native_media = native_ui = msvc_sections = False
nvidia_probe = amdvi_probe = False
doom_engine = doom_external = desktop_fixture = toolchain_client = False
if args.doom_fixture:
    from doom_fixture import make_packet, prepend_intro
    reference = (ROOT / 'reference.x86').read_bytes()
    present_path = ROOT / 'desktop-present.bin'
    present = present_path.read_bytes() if present_path.is_file() else None
    gate_path = ROOT / 'session-gate.bin'
    gate = gate_path.read_bytes() if gate_path.is_file() else None
    profile = (ROOT / 'profile.txt').read_text(encoding='ascii').strip()
    desktop_media = profile == 'desktop-media'
    desktop_doom = profile == 'desktop-doom'
    native_media = profile == 'rmlui-desktop-media'
    nvidia_probe = native_media and (ROOT / 'nvidia-pci-probe.txt').is_file()
    amdvi_probe = nvidia_probe and (ROOT / 'amdvi-efi-probe.txt').is_file()
    native_ui = profile in ('rmlui-native','rmlui-desktop','rmlui-desktop-media')
    msvc_sections = profile == 'msvc-sections'
    doom_engine = profile == 'doom-engine' or desktop_doom or native_ui or msvc_sections
    doom_external = profile == 'doom-external' or doom_engine
    desktop_fixture = (present is not None or gate is not None) and not doom_external
    image_path = ROOT / ('desktop.sbef' if desktop_fixture else 'doom.sbef')
    if native_ui:
        image_path = ROOT / 'rmlui.sbef'
    if msvc_sections:
        image_path = ROOT / 'msvc-sections.sbef'
    toolchain_client = profile.startswith('abi-') and profile.endswith('-abi-fixture')
    if toolchain_client:
        image_path = ROOT / f"{profile.removesuffix('-abi-fixture')}.sbef"
    if not image_path.is_file() and present is None and gate is None:
        image_path = ROOT / 'doom-fixed.sbef'
    external_path = ROOT / 'external-loader.bin'
    external = external_path.read_bytes() if external_path.is_file() else None
    external_image = image_path.read_bytes()
    reuse_path = ROOT / 'abi-reuse.bin'
    reuse = (reuse_path.read_bytes(), (ROOT / 'second.sbef').read_bytes()) if reuse_path.is_file() else None
    expected, doom = make_packet(reference, external_image, present, gate, external, engine=doom_engine,
                                 reuse=reuse, full_hd=full_hd_native)
    doom['toolchain_client'] = toolchain_client
    if (ROOT / 'intro.x86').is_file():
        splash = (ROOT / 'intro.x86').read_bytes()
        expected, intro_size = prepend_intro(expected, splash)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'CASM'))
        from splash_verify import read_rows
        intro_rows, _, _ = read_rows((ROOT / 'intro.casm').read_bytes(), hd=len(splash) == 1279)
    if (ROOT / 'build/Puente_Metal/METAL/INICIO.X86').read_bytes() != expected:
        raise ValueError('Paquete DOOM distinto del vector esperado')
    doom['packet_bytes'] = len(expected)
    fixture_packet = expected
if 'external-permissions' in args.casos and external is None:
    parser.error('El rechazo externo requiere el cargador externo')
if args.splash:
    if args.casos != ['normal']:
        parser.error('The splash probe requires the normal case')
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'CASM'))
    from splash_verify import read_rows
    logo, _, _ = read_rows((ROOT/'source.casm').read_bytes(), hd=args.splash_hd)
    splash_halt = 216 if args.splash_hd else 213
    splash_packet_bytes = 1279 if args.splash_hd else 508
    wait_low, wait_high = (0xb6,0xd0) if args.splash_hd else (0xb3,0xcd)
if not __debug__:
    raise RuntimeError('La prueba requiere comprobaciones assert activas; quitar PYTHONOPTIMIZE')
# Evitar que dos ejecuciones mezclen capturas, contexto o resultados.
lock_handle = (ROOT / 'build/puente-test.lock').open('a+b')
try:
    if lock_handle.seek(0, 2) == 0:
        lock_handle.write(b'0')
        lock_handle.flush()
    lock_handle.seek(0)
    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
except OSError as error:
    raise SystemExit('Ya hay una prueba del puente en ejecucion.') from error
qemu = Path(args.qemu)
share = qemu.parent / 'share'
results = []


def verify_gpu_resources(fields, display):
    bdf = display['bus'] << 8 | display['slot'] << 3 | display['function']
    if (fields.get('GPU_RES_BDF') != f'{bdf:08X}' or
        not re.fullmatch(r'[0-9A-F]{8}(?:,[0-9A-F]{8}){5}', fields.get('GPU_BARS', '')) or
        not re.fullmatch(r'[0-9A-F]{8}', fields.get('GPU_SUBSYS', ''))):
        raise ValueError('Invalid display resource snapshot')
    bar_words = fields['GPU_BARS'].split(',')
    bars = [int(word, 16) for word in bar_words]
    regions = [region for region in display['regions']
               if 0 <= region['bar'] < 6 and region['address'] >= 0]
    if not regions:
        raise ValueError('QEMU VGA has no assigned PCI resources')
    for region in regions:
        slot = region['bar']
        word = bars[slot]
        address = word & (~3 if word & 1 else ~15)
        if (word & 7) == 4:
            if slot == 5:
                raise ValueError('64-bit GPU BAR has no upper word')
            address |= bars[slot + 1] << 32
        if address != region['address']:
            raise ValueError(f'GPU BAR{slot} differs from QMP')
    result = dict(GpuResourceBdf=f'{bdf:04X}', GpuBarRegisters=bar_words, GpuSubsystemId=fields['GPU_SUBSYS'])
    if {'GPU_BAR0_LEN', 'GPU_MMIO_STATUS', 'GPU_PMC_BOOT0'} & fields.keys():
        sizes = [region['size'] for region in regions if region['bar'] == 0]
        if (len(sizes) != 1 or fields.get('GPU_BAR0_LEN') != f'{sizes[0]:08X}' or
            fields.get('GPU_MMIO_STATUS') != '00000003' or fields.get('GPU_PMC_BOOT0') != '--------'):
            raise ValueError('UEFI BAR0 length differs from QMP or NVIDIA-only read was not skipped')
        result.update(GpuBar0UefiBytes=sizes[0], GpuNvidiaMmioSkipped=True)
    return result


def verify_amdvi_firmware(log, units, register_words, present):
    words = re.search(rb'(?m)^AMDVI=([0-9A-F]{8}(?: (?:[0-9A-F]{8}|--------)){4})\r$', log)
    if not words:
        raise ValueError('Missing AMD-Vi firmware report')
    payload = words.group(1).decode('ascii')
    status, length, unit, low, high = payload.split()
    if len(units) != int(present):
        raise ValueError('QMP AMD-Vi inventory differs from the test configuration')
    if present:
        if (unit != f'{units[0]:08X}' or high != '00000000' or low not in ('FED80000', 'FED80001')
                or length == '--------' or not 48 <= int(length, 16) <= 65536
                or int(status, 16) != 6 + (int(low, 16) & 1)):
            raise ValueError(f'Unexpected QEMU AMD-Vi firmware report: {payload}')
    elif (status, length, unit, low, high) != ('00000000', '--------', '--------', '--------', '--------'):
        raise ValueError(f'Unexpected AMD-Vi report without IVRS: {payload}')
    sample = re.search(rb'(?m)^AMDVI_MMIO=([0-9A-F]{8}(?: (?:[0-9A-F]{16}|----------------)){5})\r$', log)
    if not sample:
        raise ValueError('Missing AMD-Vi MMIO report')
    mmio = sample.group(1).decode('ascii').split()
    expected = (['00000004', *register_words] if present else ['00000000'] + ['----------------'] * 5)
    if mmio != expected:
        raise ValueError(f'AMD-Vi register report {mmio} differs from {expected}')
    return dict(AmdViFirmwareVerified=True, AmdViPresent=present, AmdViReport=payload,
                AmdViMmioVerified=True, AmdViMmioReport=' '.join(mmio))


def run(case):
    coexist = amdvi_coexist and case == 'normal'
    storage = amdvi_storage and coexist
    routed = amdvi_routed and storage
    nvme_lab = amdvi_nvme and storage
    census = dma_census and case in ('normal','amdvi-missing')
    storage_handoff = storage_state and census
    payload_case = case in ('normal', 'contexto', *MUTATIONS)
    disk_case = 'normal' if ((case == 'amdvi-missing' and not nvidia_gsp_stage) or
                             (case == 'external-permissions' and not (args.doom_fixture and (desktop_media or native_media)))) else case
    image = ROOT / 'build' / f'puente-{disk_case}.img'
    before = hashlib.sha256(image.read_bytes()).hexdigest()
    prefix = ROOT / 'build' / f'puente-{case}'
    check_bootlog = (args.doom_fixture and (desktop_media or native_media) and case == 'normal') or amdvi_probe
    guest_disk = image
    if check_bootlog:
        guest_disk = Path(str(prefix) + '-bootlog.img')
        shutil.copyfile(image, guest_disk)
    variables = Path(str(prefix) + '-vars.fd')
    shutil.copyfile(share / 'edk2-i386-vars.fd', variables)
    module = ROOT / ('sbef-rejected.bin' if case == 'external-permissions' else 'sbef-module.bin')
    staging = ['-device', f'loader,file={module},addr=0x2000000,force-raw=on'] if external is not None and not (desktop_media or native_media) else []
    machine = 'pc,pit=off' if (ROOT / 'xhci-timer-fault.txt').is_file() else 'pc'
    if amdvi_probe:
        machine = 'q35'
        if case == 'normal':
            staging += ['-device', 'amd-iommu,dma-remap=on']
    wad = ROOT / 'wad-module.bin'
    if wad.is_file():
        staging += ['-device', f'loader,file={wad},addr=0x3000000,force-raw=on']
    if args.doom_fixture and desktop_media:
        root_profile = ',p3=0' if (ROOT / 'usb-root-port.txt').is_file() else ''
        staging += ['-device', f'qemu-xhci,id=bmo-xhci{root_profile}']
        if ((ROOT / 'xhci-reset.txt').is_file() or (ROOT / 'xhci-transport.txt').is_file()) and not (ROOT / 'xhci-empty-ports.txt').is_file():
            usb_version = ',usb_version=1' if (ROOT / 'usb-full-speed.txt').is_file() else ''
            staging += ['-device', f'usb-kbd,bus=bmo-xhci.0,port=1{usb_version}',
                        '-device', f'usb-mouse,bus=bmo-xhci.0,port=2{usb_version}']
        if (ROOT / 'xhci-command.txt').is_file():
            usb_version = ',usb_version=1' if (ROOT / 'usb-full-speed.txt').is_file() else ''
            hid_device = 'usb-mouse' if (ROOT / 'usb-mouse.txt').is_file() else 'usb-kbd'
            staging += ['-device', 'qemu-xhci,id=bmo-xhci-second',
                        '-device', f'{hid_device},bus=bmo-xhci-second.0{usb_version}']
    if native_media and (ROOT/'native-usb.txt').is_file():
        usb=(ROOT/'native-usb.txt').read_text().strip()
        if usb not in ('keyboard','mouse','both'):raise ValueError('Native USB profile')
        if usb=='both':
            if census:
                staging+=['-device','pcie-root-port,id=bmo-dma-root,bus=pcie.0,addr=06.0']
            placement=',bus=bmo-dma-root' if census else ',addr=05.0' if coexist else ''
            staging+=['-device','qemu-xhci,id=bmo-native-xhci'+placement]
            if not (ROOT/'native-usb-empty.txt').is_file():
                staging+=['-device','usb-kbd,bus=bmo-native-xhci.0,port=1','-device','usb-mouse,bus=bmo-native-xhci.0,port=2']
        else:
            device='usb-kbd' if usb=='keyboard' else 'usb-mouse'
            staging+=['-device','qemu-xhci,id=bmo-native-xhci','-device',f'{device},bus=bmo-native-xhci.0']
    listener = connection = qtest = None
    if coexist:
        staging += ['-nic', 'none']
        if routed:
            staging += ['-device', 'pcie-root-port,id=dma-reserve,addr=07.0,chassis=7,slot=7,bus-reserve=39',
                        '-device', 'pcie-root-port,id=dma-target,addr=08.0,chassis=8,slot=8',
                        '-device', 'edu,id=bmo-edu,bus=dma-target',
                        '-device', 'edu,id=bmo-edu-denied,addr=04.0']
        else:
            staging += ['-device', 'edu,id=bmo-edu,addr=04.0']
    if storage:
        from amdvi_ahci import DISK
        sata_image = ROOT/'amdvi-sata.raw'
        sata_image.write_bytes(DISK)
        staging += ['-drive', f'if=none,id=bmo-dma-sata,format=raw,file={sata_image},snapshot=on',
                    '-device', 'ich9-ahci,id=bmo-dma-ahci,addr=06.0',
                    '-device', 'ide-hd,drive=bmo-dma-sata,bus=bmo-dma-ahci.0']
    if storage_handoff:
        nvme = ROOT/'storage-state-nvme.raw'
        nvme.write_bytes(bytes(1024*1024))
        staging += ['-drive', f'if=none,id=bmo-nvme-state,format=raw,file={nvme},snapshot=on',
                    '-device', 'nvme,drive=bmo-nvme-state,serial=BMO-STATE,addr=07.0']
    if nvme_lab:
        from amdvi_nvme import DISK as NVME_DISK
        nvme_image = ROOT/'amdvi-nvme.raw'
        nvme_image.write_bytes(NVME_DISK)
        staging += ['-drive', f'if=none,id=bmo-dma-nvme,format=raw,file={nvme_image},snapshot=on',
                    '-device', 'nvme,id=bmo-nvme,drive=bmo-dma-nvme,serial=BMO-DMA,addr=09.0']
    if coexist or census:
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(8)
        staging += ['-qtest-log', 'none',
                    '-qtest', f'tcp:127.0.0.1:{listener.getsockname()[1]}']
    process = subprocess.Popen([
        str(qemu), '-machine', machine,
        '-cpu', args.cpu, '-accel', 'tcg', '-m', f'{args.ram_mib}M', '-smp', '1',
        '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={share / "edk2-x86_64-code.fd"}',
        '-drive', f'if=pflash,format=raw,unit=1,file={variables}',
        '-drive', f'file={guest_disk},format=raw,if=ide,snapshot={"off" if check_bootlog else "on"}',
        '-vga', 'std', '-display', 'none', '-serial', f'file:{prefix}-serial.log',
        *(['-global','VGA.xres=1920','-global','VGA.yres=1080'] if full_hd and case=='normal' else
          ['-global','VGA.xres=1024','-global','VGA.yres=768'] if (ROOT/'low-gop.txt').is_file() else []),
        '-qmp', 'stdio', '-monitor', 'none', '-no-reboot',
        '-d', 'guest_errors,int', '-D', str(prefix) + '-cpu.log', *staging],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', cwd=ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
    messages = queue.Queue()
    def reader():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                pass
    threading.Thread(target=reader, daemon=True).start()
    sequence = 0

    def command(name, arguments=None):
        nonlocal sequence
        sequence += 1
        request = {'execute': name, 'id': sequence}
        if arguments is not None:
            request['arguments'] = arguments
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            response = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if response.get('id') == sequence:
                if 'error' in response:
                    raise RuntimeError(str(response['error']))
                return response['return']
        raise TimeoutError(name)

    def memory(address, size, label):
        path = Path(str(prefix) + '-' + label + '.bin')
        # Windows scanners can temporarily hold a dump between QMP polls.
        for attempt in range(5):
            try:
                command('pmemsave', dict(val=address, size=size, filename=str(path)))
                return path.read_bytes()
            except (RuntimeError, PermissionError) as error:
                transient = isinstance(error, PermissionError) or (
                    'Could not open' in str(error) and 'Permission denied' in str(error))
                if attempt == 4 or not transient:
                    raise
                time.sleep(0.05 * (attempt + 1))

    captured = None
    frames = set()
    try:
        if listener:
            from amdvi_xhci import SocketQTest
            connection, _ = listener.accept()
            connection.settimeout(5)
            qtest = SocketQTest(connection)
        command('qmp_capabilities')
        if doom and doom['session']:
            from desktop_session_capture import verify_external_rejection, verify_session
            if doom_engine:
                if msvc_sections:
                    from msvc_capture import verify_sections
                    return verify_sections(command, memory, prefix, external_image, case, ROOT / 'msvc-symbols.json')
                if native_ui:
                    from rmlui_native_capture import verify_native_ui
                    result = verify_native_ui(command, memory, prefix, external_image, case, ROOT / 'ui-symbols.json',
                                              amdvi_coexist=qtest if coexist else None,
                                              dma_census=qtest if census else None)
                    if amdvi_probe or (nvidia_probe and case == 'normal'):
                        devices = [device for bus in command('query-pci') for device in bus['devices']]
                        if case == 'normal':
                            result['GpuQmpDisplay'] = [device for device in devices if device['class_info']['class'] >> 8 == 3]
                        if amdvi_probe:
                            result['AmdViQmpUnits'] = [
                                device['bus'] << 8 | device['slot'] << 3 | device['function']
                                for device in devices if device['id']['vendor'] == 0x1022 and device['id']['device'] == 0x1419
                            ]
                            result['AmdViQmpRegisters'] = []
                            if case == 'normal':
                                for offset in (0x18, 0, 8, 0x10, 0x2020):
                                    data = memory(0xfed80000 + offset, 8, f'amdvi-reg-{offset:04x}')
                                    result['AmdViQmpRegisters'].append(f'{int.from_bytes(data, "little"):016X}')
                    return result
                from doom_engine_capture import verify_engine
                return verify_engine(command, memory, prefix, external_image, case, desktop=desktop_doom)
            if case == 'external-permissions':
                return verify_external_rejection(command, memory, external_image)
            if (ROOT / 'welcome.txt').is_file():
                from welcome_capture import verify_welcome
                return verify_welcome(command, memory, prefix, intro_rows, skip=args.welcome_skip)
            if profile == 'rmlui-raster-probe':
                from rmlui_capture import verify_raster
                return verify_raster(command, memory, prefix, ROOT / 'raster-expected.bin')
            if external is not None:
                doom['sbef_sha256'] = hashlib.sha256(external_image).hexdigest()
            if doom_external:
                from doom_external_capture import verify_doom_external
                return verify_doom_external(command, memory, prefix, fixture_packet, external_image, wad)
            return verify_session(command, memory, prefix, fixture_packet, intro_rows, doom,
                                  external_image if external is not None else None, desktop_media=desktop_media)
        deadline = time.monotonic() + 45
        last_registers = ''
        context = None
        saved_context_address = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('QEMU termino: ' + process.stderr.read()[-1000:])
            last_registers = command('human-monitor-command', {'command-line': 'info registers'})
            match = re.search(r'RBP=([0-9a-fA-F]+)', last_registers)
            if saved_context_address is None and not payload_case and case != 'salida':
                serial = Path(str(prefix) + '-serial.log').read_text(encoding='utf-8', errors='replace')
                if 'Pulse una tecla para volver.' in serial:
                    # Dentro de ReadKeyStroke el compilador de UEFI puede usar RBP.
                    # Localizar la reserva propia por cabecera alineada, solo en RAM de esta VM.
                    for start in range(0xf000000, -1, -0x1000000):
                        block = memory(start, 0x1000000, 'scan')
                        for page in range(0, len(block) - 0xb0, 4096):
                            if block[page:page + 8] == b'METAL64!' and struct.unpack_from('<Q', block, page + 8)[0] % 4096 == 0:
                                saved_context_address = start + page
                                break
                        if saved_context_address is not None:
                            break
                    Path(str(prefix) + '-scan.bin').unlink(missing_ok=True)
            if match or saved_context_address is not None:
                address = saved_context_address if saved_context_address is not None else int(match[1], 16)
                if 0x100000 <= address <= args.ram_mib * 1024 * 1024 - 0x20000:
                    candidate = memory(address, 0xb0, 'context')
                    if candidate[:8] == b'METAL64!':
                        ebs, returned, failed = (struct.unpack_from('<I', candidate, p)[0] for p in (0x78, 0x98, 0x9c))
                        if (args.splash or intro_rows) and ebs == 1 and 'CPL=0' in last_registers and 'HLT=0' in last_registers:
                            frame = register(last_registers, 'R12')
                            if frame in (1,2) and frame not in frames:
                                command('stop')
                                try:
                                    stopped = command('human-monitor-command', {'command-line':'info registers'})
                                    code_base = struct.unpack_from('<Q', candidate, 8)[0]
                                    low, high = ((0xb6, 0xd0) if len(intro_rows) == 64 else (0xb3, 0xcd)) if intro_rows else (wait_low, wait_high)
                                    if register(stopped, 'R12') == frame and low <= register(stopped,'RIP')-code_base < high:
                                        compare_frame(memory,candidate,intro_rows or logo,frame)
                                        command('screendump', {'filename':str(prefix)+f'-frame-{frame}.png','format':'png'})
                                        frames.add(frame)
                                finally:
                                    command('cont')
                        if (failed == 1 or ((returned or failed == 2 or (args.halt and payload_case and ebs == 1)) and 'HLT=1' in last_registers)):
                            context = candidate
                            captured = address
                            break
            time.sleep(0.1)
        command('screendump', {'filename': str(prefix) + '.png', 'format': 'png'})
        Path(str(prefix) + '-registers.txt').write_text(last_registers, encoding='utf-8')
        if context is None:
            raise AssertionError('No se alcanzo contexto final; revisar captura y registro CPU')
        ebs, returned, failed = (struct.unpack_from('<I', context, p)[0] for p in (0x78, 0x98, 0x9c))
        if case == 'salida':
            attempts_left, attempted = (struct.unpack_from('<I', context, p)[0] for p in (0x6c, 0x7c))
            assert (ebs, returned, failed, attempts_left, attempted) == (0, 0, 2, 0, 1)
            assert 'HLT=1' in last_registers, 'No se detuvo tras agotar reintentos'
            return dict(Case=case, Passed=True, FaultInjection='MapKey cero en copia de prueba',
                        BootServicesExited=False, PayloadReturned=False, BoundedRetries=3)
        if not payload_case:
            assert (ebs, returned, failed) == (0, 0, 1), 'El paquete rechazado salio de UEFI o ejecuto el programa'
            reason_pointer = struct.unpack_from('<Q', context, 0xa0)[0]
            reason = memory(reason_pointer, 128, 'reason').decode('utf-16-le').split('\0', 1)[0]
            expected = 'no se pudo leer' if case == 'ausente' else 'paquete FAGRAW64 invalido'
            assert expected in reason, f'Rechazo distinto del esperado: {reason}'
            return dict(Case=case, Passed=True, BootServicesExited=False, PayloadReturned=False, Reason=reason)
        assert (ebs, returned, failed) == (1, 0 if args.halt else 1, 0), 'Estado final distinto del contrato'
        assert 'CPL=0' in last_registers and 'HLT=1' in last_registers, 'No se detuvo en nivel 0'
        packet = (ROOT / 'build/Puente_Metal/METAL/INICIO.X86').read_bytes()
        if case in MUTATIONS:
            packet = mutated_packet(packet, case)
        code = struct.unpack_from('<Q', context, 8)[0]
        assert memory(code, len(packet) - 24, 'code') == packet[24:], 'No ejecuto la copia exacta del cuerpo propio'
        halt_offset = splash_halt + 1 if args.splash else 866 if args.hot_unmap else intro_size + 896 if args.abi_probe else 662 if args.user_fault else 471 if args.paging else 426 if args.frame_cycle else 215 if args.memory else 136 if args.fault else 48 if args.stack else 6 if args.identify else 2
        if args.halt:
            terminal = 'FA 31 C0 0F A2 F4 EB FD' if args.identify else 'FA F4 EB FD'
            if args.splash:
                assert len(packet) == splash_packet_bytes and packet[24+splash_halt:24+splash_halt+3] == bytes.fromhex('F4 EB FD'), 'Terminal de splash distinto'
            elif args.fault:
                assert len(packet) == 162 and packet[24+135:] == bytes.fromhex('F4 EB FD'), 'Terminal de excepcion distinto'
            elif args.memory:
                assert len(packet) == 241 and packet[24+214:] == bytes.fromhex('F4 EB FD'), 'Terminal de memoria distinto'
            elif args.frame_cycle:
                assert len(packet) == 498 and packet[24+425:24+428] == bytes.fromhex('F4 EB FD'), 'Terminal de ciclo distinto'
            elif args.paging:
                assert len(packet) == 497 and packet[24+470:] == bytes.fromhex('F4 EB FD'), 'Terminal de paginacion distinto'
            elif args.user_fault:
                assert len(packet) == 740 and packet[24+661:24+664] == bytes.fromhex('F4 EB FD'), 'Terminal de CPL3 distinto'
            elif args.abi_probe:
                expected_size = doom['packet_bytes'] if doom else 1263
                terminal_offset = 24 + intro_size + 895
                assert len(packet) == expected_size and packet[terminal_offset:terminal_offset+3] == bytes.fromhex('F4 EB FD'), 'Terminal ABI distinto'
            elif args.hot_unmap:
                assert len(packet) == 954 and packet[24+865:24+868] == bytes.fromhex('F4 EB FD'), 'Terminal de revocacion distinto'
            elif args.stack:
                assert len(packet) == 74 and packet[24+47:] == bytes.fromhex('F4 EB FD'), 'Terminal de contexto distinto'
            else:
                assert packet[24:] == bytes.fromhex(terminal), 'Terminal distinto'
            rip = int(re.search(r'RIP=([0-9a-fA-F]+)', last_registers)[1], 16)
            flags = int(re.search(r'RFL=([0-9a-fA-F]+)', last_registers)[1], 16)
            assert rip == code + halt_offset and not flags & 0x200, 'No se detuvo en HLT propio con IF=0'
        size, stride = struct.unpack_from('<Q', context, 0x50)[0], struct.unpack_from('<Q', context, 0x60)[0]
        if memory_case:
            assert 40 <= stride <= 256 and stride <= size <= 65536 and size % stride == 0, 'Geometria de mapa distinta'
        descriptors = memory(captured + 0x1000, size, 'map')
        assert stride >= 40 and size % stride == 0, 'Mapa de memoria invalido'
        regions = [struct.unpack_from('<I4xQQQQ', descriptors, off) for off in range(0, size, stride)]
        assert any(kind == 1 and base <= code and code + 4096 <= base + pages * 4096 for kind, base, virt, pages, attr in regions)
        assert any(kind == 2 and base <= captured and captured + 0x20000 <= base + pages * 4096 for kind, base, virt, pages, attr in regions)
        stack_result = {}
        if args.stack:
            low, top = captured + 0x13000, captured + 0x14000
            old, new, supplied, status = (register(last_registers, n) for n in ('RSI', 'RSP', 'RDI', 'RAX'))
            assert old == captured + 0x1fff8, 'Pila del puente fuera del contrato'
            page = memory(low, top - low, 'own-stack')
            if case == 'contexto':
                assert (supplied, status, new) == (0, 0, old) and page == bytes(4096), 'Se acepto contexto invalido'
            else:
                assert (supplied, status, new) == (captured, 1, top) and new % 16 == 0, 'Pila propia invalida'
                assert register(last_registers, 'RDX') == 0x324F4D42, 'POP no recupero la marca'
                assert page == bytes(4088) + struct.pack('<Q', 0x324F4D42), 'Escritura inesperada en la pila'
            stack_result = dict(ContextAccepted=status == 1, StackBefore=f'0x{old:X}',
                                StackAfter=f'0x{new:X}', StackPageTouched=case == 'normal',
                                FaultInjection='RDI=0 al entregar' if case == 'contexto' else None)
        framebuffer = struct.unpack_from('<Q', context, 0x10)[0]
        scan = struct.unpack_from('<I', context, 0x28)[0]
        pixels = memory(framebuffer, scan * 48 * 4, 'pixels')
        expected = bytearray(len(pixels))
        font = (ROOT / 'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI').read_bytes()[0x2000:0x2800]
        texts = ('METAL64: BootServices cerrados.',) if args.halt else ('METAL64: BootServices cerrados.', 'GENESIS', 'Programa propio retorno. CPU detenida.')
        for row, text in enumerate(texts):
            for col, character in enumerate(text):
                for y in range(16):
                    bits = font[ord(character) * 16 + y]
                    for x in range(8):
                        if bits & (0x80 >> x):
                            offset = ((row * 16 + y) * scan + col * 8 + x) * 4
                            expected[offset:offset + 4] = b'\xff\xff\xff\0'
        assert pixels == expected, 'Framebuffer distinto del texto propio esperado'
        result = dict(Case=case, Passed=True, BootServicesExited=True, PayloadReturned=not args.halt, OwnHalt=args.halt,
                    InstructionPointerOffset=halt_offset if args.halt else None, InterruptsMasked=True if args.halt else None,
                    Ring=0, OwnFramebufferTextVerified=True, Context=f'0x{captured:X}',
                    PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(), **stack_result)
        if args.identify:
            result['CPUIdentification'] = identify(last_registers)
        if args.fault:
            result.update(fault_evidence(memory,last_registers,captured,code,case=='contexto'))
        if case in MUTATIONS:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from host.diagnostics import Rejection
            from host.sbef.format import inspect
            try:
                inspect(packet[SBEF_OFFSET:])
            except Rejection as error:
                result['HostDiagnostic'] = error.report()
            else:
                raise ValueError('ABI-PROBE: el lector HOST admitio el SBEF mutado')
            base = captured + 0x13000
            assert register(last_registers, 'R12') == 0 and register(last_registers, 'R13') == register(last_registers, 'CR3'), 'CASM activo un SBEF rechazado'
            assert memory(base + 0x5000, 8192, 'rejected-user-pages') == bytes(8192), 'CASM copio bytes rechazados'
            assert memory(base + 0x7310, 8, 'rejected-syscalls') == bytes(8), 'Se ejecuto una llamada de usuario'
            result.update(SbefAccepted=False, SyscallCount=0)
        elif user_case:
            result.update(user_fault_evidence(memory,last_registers,captured,code+intro_size,case=='contexto',
                                              abi_probe=args.abi_probe,hot_unmap=args.hot_unmap,doom=doom))
        if memory_case:
            if args.paging:
                result.update(paging_evidence(memory,last_registers,regions,captured,code,case=='contexto'))
            else:
                result.update(memory_evidence(memory,last_registers,regions,captured,code,case=='contexto',cycle=args.frame_cycle))
            result['MemoryMapBytes'] = size
        if args.splash:
            assert register(last_registers, 'R12') == 3 and frames == {1,2}, 'Faltan cuadros completos'
            compare_frame(memory,context,logo,3)
            result['FramesVerified'] = [1,2,3]
        if intro_rows:
            assert frames == {1, 2}, 'Faltan cuadros completos de la intro'
            compare_frame(memory, context, intro_rows, 3)
            result['FramesVerified'] = [1, 2, 3]
        if doom and doom['desktop']:
            order = struct.unpack_from('<I', context, 0x2c)[0]
            colors = [(0x82, 0x5c, 0xff), (0xff, 0xd8, 0x5a)]
            row = b''.join(bytes((*(color[::-1] if order else color), 0)) * 64 for color in colors)
            region = memory(framebuffer + (64*scan+16)*4, (31*scan+128)*4, 'desktop')
            assert all(region[y*scan*4:y*scan*4+512] == row for y in range(32)), 'Pixeles Rust distintos'
            result['DesktopPixelsVerified'] = 128 * 32
        return result
    finally:
        if qtest:
            qtest.channel.close()
        if connection:
            connection.close()
        if listener:
            listener.close()
        if args.doom_fixture and desktop_media and process.poll() is None:
            try:
                command('screendump', {'filename': str(prefix) + '-media-last.png', 'format': 'png'})
            except (RuntimeError, TimeoutError, OSError, queue.Empty):
                pass
        if process.poll() is None:
            try:
                command('quit')
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait()
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()
        assert hashlib.sha256(image.read_bytes()).hexdigest() == before, 'La imagen base fue modificada'
        if storage and sata_image.read_bytes()!=DISK:
            raise ValueError('La imagen SATA del laboratorio cambio')
        if storage_handoff and nvme.read_bytes()!=bytes(1024*1024):
            raise ValueError('La imagen NVMe del laboratorio cambio')
        if nvme_lab and nvme_image.read_bytes()!=NVME_DISK:
            raise ValueError('La imagen NVMe traducida del laboratorio cambio')


for case in args.casos:
    try:
        result = run(case)
        if (args.doom_fixture and (desktop_media or native_media) and case == 'normal') or amdvi_probe:
            from desktop_session_capture import verify_bootlog_file
            prefix = ROOT / 'build' / f'puente-{case}'
            if native_media:
                from fat32_read import Fat32
                fs=Fat32(Path(str(prefix)+'-bootlog.img'))
                try:
                    media_prefix = 'BMO-X2/GPU' if nvidia_probe else 'BMO-X2/DESKTOP'
                    log_name = 'GPULOG.TXT' if nvidia_probe else 'BOOTLOG.TXT'
                    log=fs.file_bytes(f'{media_prefix}/{log_name}',4096)
                    loaded=fs.file_bytes(f'{media_prefix}/DESKTOP.SBF')
                    expected_image = (ROOT / 'rejected.sbef').read_bytes() if case == 'external-permissions' else external_image
                    if loaded!=expected_image or not log.startswith(b'BMO-X2 DESKTOP UEFI PRE-EBS\r\n'):
                        raise ValueError('Native FAT32 payload/report differs')
                    Path(str(prefix)+'-'+log_name).write_bytes(log)
                    if nvidia_gsp_sample:
                        samples = [line for line in log.splitlines() if line.startswith(b'GSP1=')]
                        if samples != [b'GSP1=--------,--------,--------']:
                            raise ValueError('GA106 GSP reads must be skipped on QEMU standard VGA')
                        result['GpuGspSampleSkipped'] = True
                    if nvidia_gsp_stage:
                        stage = [line for line in log.splitlines() if line.startswith(b'GSPLOAD=')]
                        expected = {'normal': 5, 'external-permissions': 4, 'amdvi-missing': 1}[case]
                        if stage != [f'GSPLOAD={expected:08X}'.encode('ascii')]:
                            raise ValueError(f'Unexpected FAT32 GSP staging result: {stage!r}')
                        result['GspStageStatus'] = expected
                    if amdvi_probe:
                        result.update(verify_amdvi_firmware(log, result.pop('AmdViQmpUnits'),
                                                            result.pop('AmdViQmpRegisters'), case == 'normal'))
                    if amdvi_post and case == 'normal':
                        pre = result['AmdViMmioReport'].split()[1:]
                        post = result['AmdViPostReport'].split()[1:]
                        if pre != post:
                            raise ValueError(f'AMD-Vi QEMU register values changed across EBS: {pre} != {post}')
                    if nvidia_probe and case == 'normal':
                        values = dict(line.split('=', 1) for line in log.decode('ascii').splitlines()
                                      if line.startswith('GPU_'))
                        expected = {
                            'GPU_PROBE': 'PCI_RO', 'GPU_DISPLAY_COUNT': '00000001',
                            'GPU_NVIDIA_COUNT': '00000000', 'GPU_NVIDIA_BDF': '--------',
                            'GPU_NVIDIA_ID': '--------', 'GPU_NVIDIA_CMD': '--------',
                        }
                        if any(values.get(key) != value for key, value in expected.items()):
                            raise ValueError('Unexpected PCI result for QEMU standard VGA')
                        display, = result.pop('GpuQmpDisplay')
                        if values.keys() != expected.keys():
                            result.update(verify_gpu_resources(values, display))
                        result['NvidiaPciProbeVerified'] = True
                        result['GpuDisplayFunctions'] = 1
                        result['GpuNvidiaFunctions'] = 0
                finally:fs.close()
            else:
                verify_bootlog_file(Path(str(prefix) + '-bootlog.img'), prefix)
            result['BootLogFat32Verified'] = True
    except Exception as error:
        result = dict(Case=case, Passed=False, Error=str(error))
    results.append(result)
    print(json.dumps(result, ensure_ascii=True))
Path('build/puente-test-results.json').write_text(json.dumps(dict(Passed=sum(c['Passed'] for c in results), Total=len(results), Cases=results), indent=2) + '\n', encoding='utf-8')
if not all(c['Passed'] for c in results):
    raise SystemExit(1)
