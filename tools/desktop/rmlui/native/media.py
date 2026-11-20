"""Stage the native desktop in a separate FAT32 directory; verify UEFI disk reads in QEMU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid
from build import ROOT,OUT,command
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/boot'))
from doom_fixture import make_packet,prepend_intro
from stage_bmo_x2 import bridge_variant
from wake import check
from fat32_read import Fat32

def check_context_stage(llvm, obj, name):
    symbols=subprocess.check_output([llvm/'llvm-nm.exe','--format=posix',obj],text=True)
    positions={fields[0]:int(fields[2],16) for line in symbols.splitlines()
               if len(fields:=line.split())>=3 and fields[0] in (name+'_begin',name+'_end')}
    if not 0<positions[name+'_end']-positions[name+'_begin']<=2048:
        raise ValueError('Context code stage exceeds its half page: '+name)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('abi_run',type=Path);p.add_argument('splash_run',type=Path)
    p.add_argument('--low-gop',action='store_true')
    p.add_argument('--msvc-panel',action='store_true',help='Use the optional MSVC desktop build')
    p.add_argument('--usb',choices=['keyboard','mouse','both'],help='Mediated xHCI profile; both uses the dynamic USB2 root transport')
    p.add_argument('--usb-empty-ports',action='store_true',help='QEMU rejection test; never a metal candidate')
    p.add_argument('--nvidia-probe', action='store_true', help='Read PCI display inventory before ExitBootServices')
    p.add_argument('--amdvi-probe', action='store_true', help='Add read-only AMD-Vi firmware inventory to the NVIDIA profile')
    p.add_argument('--amdvi-post', action='store_true', help='Take a second AMD-Vi snapshot after ExitBootServices')
    p.add_argument('--amdvi-coexist', action='store_true', help='Exercise virtual EDU and USB DMA together in QEMU')
    p.add_argument('--amdvi-guest-dma', action='store_true', help='Let the guest program AMD-Vi in the virtual lab')
    args=p.parse_args()
    if args.usb_empty_ports and args.usb!='both':p.error('--usb-empty-ports requires --usb both')
    if args.amdvi_probe and not args.nvidia_probe:p.error('--amdvi-probe requires --nvidia-probe')
    if args.amdvi_post and (not args.amdvi_probe or args.usb!='both' or args.msvc_panel or args.usb_empty_ports):
        p.error('--amdvi-post requires the NVIDIA AMD-Vi profile with USB both')
    if args.amdvi_coexist and not args.amdvi_post:p.error('--amdvi-coexist requires --amdvi-post')
    if args.amdvi_guest_dma and not args.amdvi_coexist:p.error('--amdvi-guest-dma requires --amdvi-coexist')
    abi,splash=args.abi_run.resolve(),args.splash_run.resolve()
    for path in (abi,splash):
        if path.parent!=ROOT/'build/CASM':raise ValueError('Run outside build/CASM')
        check(path)
    if (abi/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-abi-probe-0.1' or (splash/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-splash-0.1':
        raise ValueError('ABI probe and compact CASM cat required')
    variant='desktop-usb-'+args.usb if args.usb else 'desktop'
    if args.amdvi_post:variant+='-amdvi-post'
    app=OUT/(variant + ('-msvc' if args.msvc_panel else ''))
    hashes=json.loads((app/'artifacts.json').read_text())
    for name,digest in hashes.items():
        if hashlib.sha256((app/name).read_bytes()).hexdigest()!=digest:raise ValueError('Stale desktop build: '+name)
    run=ROOT/'build/CASM'/('run-rmlui-media-'+uuid.uuid4().hex[:12]);run.mkdir()
    (run/'gop-regions.txt').write_text('cpu-gop\n',encoding='ascii')
    if args.nvidia_probe:
        (run/'nvidia-pci-probe.txt').write_text('pci-read-only\n', encoding='ascii')
    if args.amdvi_probe:
        (run/'amdvi-efi-probe.txt').write_text('firmware-read-only\n', encoding='ascii')
    if args.amdvi_post:
        (run/'amdvi-post-probe.txt').write_text('post-ebs-read-only\n', encoding='ascii')
    if args.amdvi_coexist:
        (run/'amdvi-coexist-probe.txt').write_text('qemu-only-edu-xhci\n', encoding='ascii')
    if args.amdvi_guest_dma:
        (run/'amdvi-guest-dma.txt').write_text('qemu-only-guest-iommu\n', encoding='ascii')
    if args.low_gop:(run/'low-gop.txt').write_text('QEMU VGA preferred 1024x768\n',encoding='ascii')
    if args.usb:(run/'native-usb.txt').write_text(args.usb+'\n',encoding='ascii')
    if args.usb_empty_ports:(run/'native-usb-empty.txt').write_text('QEMU fault test\n',encoding='ascii')
    llvm=Path(os.environ['ProgramFiles'])/'LLVM/bin'
    extra=12288 if args.usb=='both' else 8192 if args.usb else 4096
    amdvi_offset=0x3000+extra
    units=[('allocator','kernel/boot/bridge/desktop_media_alloc.S'),('reader','kernel/boot/bridge/desktop_media_read.S'),
        ('gate','kernel/syscalls/session_gate.S'),('loader','kernel/loader/doom_engine_loader.S')]
    for name,source in units:
        flags=['-DRMLUI_USB','-DDESKTOP_MEDIA','-DXHCI_COMMAND_PROBE'] if args.usb else []
        if args.usb=='both':flags+=['-DXHCI_NATIVE_DUAL']
        if args.nvidia_probe and name == 'reader':flags+=['-DBMO_NVIDIA_PCI_PROBE']
        if args.amdvi_probe and name == 'reader':flags+=[f'-DBMO_AMDVI_EFI_OFFSET={amdvi_offset}']
        if args.amdvi_post and name in ('reader','gate'):flags+=['-DBMO_AMDVI_POST']
        if args.amdvi_guest_dma and name=='gate':flags+=['-DBMO_AMDVI_GUEST_DMA']
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-DRMLUI_MEDIA','-DRMLUI_NATIVE',
            '-DRMLUI_GOP_REGIONS','-DDOOM_ENGINE','-DDESKTOP_DOOM',*flags,
            '-c',ROOT/source,'-o',run/(name+'.o')],'compile-media-'+name)
        if args.amdvi_post and name=='reader':check_context_stage(llvm,run/'reader.o','gop_stage')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',run/(name+'.o'),run/(name+'.bin')],'extract-media-'+name)
    sbef=(app/'rmlui.sbef').read_bytes();reference=(abi/'INICIO.X86').read_bytes()
    gate=(run/'gate.bin').read_bytes();loader=(run/'loader.bin').read_bytes()
    packet,_=make_packet(reference,sbef,session_gate=gate,external=loader,engine=True)
    intro=(splash/'INICIO.X86').read_bytes();packet,_=prepend_intro(packet,intro)
    image=bridge_variant(native_ui=True,nvidia_probe=args.nvidia_probe)
    reader=(run/'reader.bin').read_bytes();allocator=(run/'allocator.bin').read_bytes()
    if len(image)!=0x3000 or len(reader)>4096 or len(allocator)>0xf0 or image[0x267:0x26c]!=bytes.fromhex('e894050000'):
        raise ValueError('Native EFI extension exceeds verified slots')
    struct.pack_into('<i',image,0x268,0x3000-0x267-5)
    if args.amdvi_probe:extra+=4096
    for offset,old in ((0x5c,0x2e00),(0x90,0x4000),(0x150,0x2e00),(0x158,0x2e00)):
        if struct.unpack_from('<I',image,offset)[0]!=old:raise ValueError('EFI PE header changed')
        struct.pack_into('<I',image,offset,old+extra)
    image.extend(reader.ljust(4096,b'\0'))
    if args.usb:
        flags=['-DRMLUI_USB']+(['-DXHCI_NATIVE_DUAL'] if args.usb=='both' else ['-DXHCI_COMMAND_PROBE'])+(['-DXHCI_MOUSE_PROBE'] if args.usb=='mouse' else [])
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-x','assembler-with-cpp',*flags,'-c',
            ROOT/'kernel/drivers/bus/xhci_inventory.inc','-o',run/'xhci.o'],'compile-native-xhci')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',run/'xhci.o',run/'xhci.bin'],'extract-native-xhci')
        stage=(run/'xhci.bin').read_bytes()
        budget=8192 if args.usb=='both' else 4096
        if not 0<len(stage)<=budget:raise ValueError('USB stage exceeds its explicit reserved code pages')
        image.extend(stage.ljust(budget,b'\0'))
    if args.amdvi_probe:
        source=ROOT/'kernel/drivers/bus/amdvi/firmware_probe.S'
        native_probe=run/'amdvi-firmware.o'
        flags=['-DBMO_AMDVI_POST'] if args.amdvi_post else []
        if args.amdvi_coexist:flags+=['-DBMO_AMDVI_COEXIST']
        if args.amdvi_guest_dma:flags+=['-DBMO_AMDVI_GUEST_DMA']
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf',*flags,'-c',source,'-o',native_probe],'compile-amdvi-firmware')
        if args.amdvi_post:check_context_stage(llvm,native_probe,'amdvi_post')
        relocations=subprocess.check_output([llvm/'llvm-objdump.exe','-r',native_probe],text=True)
        if 'RELOCATION RECORDS' in relocations:raise ValueError('AMD-Vi firmware inventory must be position independent')
        raw_probe=native_probe.with_suffix('.bin')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',native_probe,raw_probe],'extract-amdvi-firmware')
        stage=raw_probe.read_bytes()
        if len(image)!=amdvi_offset or not 0<len(stage)<=4096:raise ValueError('AMD-Vi EFI slot mismatch')
        image.extend(stage.ljust(4096,b'\0'))
    image[0x400:0x400+len(allocator)]=allocator
    files={'reference.x86':reference,'rmlui.sbef':sbef,'session-gate.bin':gate,'external-loader.bin':loader,
        'INICIO.X86':packet,'intro.x86':intro,'intro.casm':(splash/'source.casm').read_bytes(),'profile.txt':b'rmlui-desktop-media\n',
        'ui-symbols.json':(app/'symbols.json').read_bytes()}
    for name,data in files.items():(run/name).write_bytes(data)
    efi=run/'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI';efi.parent.mkdir(parents=True);efi.write_bytes(image)
    payload=run/'build/Puente_Metal/METAL/INICIO.X86';payload.parent.mkdir(parents=True);payload.write_bytes(packet)
    scripts=ROOT/'tools/boot';shell=shutil.which('powershell.exe')
    command([shell,'-NoProfile','-ExecutionPolicy','Bypass','-File',scripts/'disk.ps1','-OutputRoot',run,'-Programa','INICIO.X86','-GPT'],'create-native-fat32')
    bad=bytearray(sbef);struct.pack_into('<I',bad,116,7);(run/'rejected.sbef').write_bytes(bad)
    prepare_flags = ['--nvidia-probe'] if args.nvidia_probe else []
    for case,appfile in [('external-permissions',run/'rejected.sbef'),('normal',run/'rmlui.sbef')]:
        command([sys.executable,scripts/'prepare.py','--workspace',run,'--bmo-x2-folder','--desktop',appfile,'--native-ui',*prepare_flags],'prepare-ui-'+case)
        if case!='normal':(run/'build/puente-normal.img').replace(run/'build/puente-external-permissions.img')
    cases=['normal','external-permissions']+(['amdvi-missing'] if args.amdvi_post else [])
    command([sys.executable,scripts/'probe.py','--workspace',run,'--halt','--abi-probe','--doom-fixture',
        '--ram-mib','1024','--casos',*cases],'qemu-fat32-desktop',cwd=run)
    report=json.loads((run/'build/puente-test-results.json').read_text())
    if report['Passed']!=len(cases) or not report['Cases'][0].get('BootLogFat32Verified'):raise ValueError('Missing disk evidence')
    if args.nvidia_probe and (not report['Cases'][0].get('GpuBar0UefiBytes') or
                             not report['Cases'][0].get('GpuNvidiaMmioSkipped')):
        raise ValueError('Missing UEFI BAR0 bounds or device guard evidence')
    if args.amdvi_probe and not all(case.get('AmdViMmioVerified') for case in report['Cases']):
        raise ValueError('Missing AMD-Vi MMIO evidence')
    if args.amdvi_post and not all(report['Cases'][i].get('AmdViPostVerified') for i in (0,2)):
        raise ValueError('Missing post-EBS AMD-Vi evidence')
    if args.amdvi_coexist and not report['Cases'][0].get('AmdViCoexistVerified'):
        raise ValueError('Missing simultaneous EDU and USB evidence')
    if args.amdvi_guest_dma and report['Cases'][0].get('DmaIssuer')!='Ring 0 guest':
        raise ValueError('Missing guest-owned AMD-Vi evidence')
    media_prefix = 'BMO-X2/GPU' if args.nvidia_probe else 'BMO-X2/DESKTOP'
    fs=Fat32(run/'build/puente-normal.img')
    try:
        if fs.file_bytes(f'{media_prefix}/DESKTOP.SBF')!=sbef or fs.file_bytes(f'{media_prefix}/INICIO.X86',4096)!=packet:
            raise ValueError('FAT32 staged bytes differ')
    finally:fs.close()
    media=run/'media'
    boot_name = 'NVIDIA.EFI' if args.nvidia_probe else 'DESKTOP.EFI'
    staged={f'EFI/BMO-X2/{boot_name}':image,f'{media_prefix}/INICIO.X86':packet,f'{media_prefix}/DESKTOP.SBF':sbef}
    for name,data in staged.items():
        target=media/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report.update(run=run.name,evidence='QEMU',disk_sbef=True,physical_boot=False,physical_usb_proven=False,
        display_backend='cpu-gop',
        nvidia_pci_probe=args.nvidia_probe, amdvi_efi_probe=args.amdvi_probe, amdvi_mmio_probe=args.amdvi_probe,
        amdvi_post_probe=args.amdvi_post,
        amdvi_coexist=args.amdvi_coexist,
        amdvi_guest_dma=args.amdvi_guest_dma,
        qemu_only=bool(args.usb),usb_profile=args.usb,
        usb_empty_ports=args.usb_empty_ports,
        hardware_profile='amd149c-usb2-root-experimental' if args.usb=='both' and not args.usb_empty_ports else None,
        note='Separate desktop candidate; no QEMU loader device, UEFI reads real FAT32 files.',
        files={name:hashlib.sha256(data).hexdigest() for name,data in staged.items()})
    (run/'qemu-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    (run/'qemu-run.json').write_text(json.dumps(dict(cpu='qemu64',ram_mib=1024))+'\n',encoding='ascii')
    (media/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print('Verified candidate: '+str(media))

if __name__=='__main__':main()
