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

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('abi_run',type=Path);p.add_argument('splash_run',type=Path)
    p.add_argument('--low-gop',action='store_true')
    p.add_argument('--usb',choices=['keyboard','mouse','both'],help='Mediated xHCI profile; both uses the dynamic USB2 root transport')
    p.add_argument('--usb-empty-ports',action='store_true',help='QEMU rejection test; never a metal candidate')
    args=p.parse_args()
    if args.usb_empty_ports and args.usb!='both':p.error('--usb-empty-ports requires --usb both')
    abi,splash=args.abi_run.resolve(),args.splash_run.resolve()
    for path in (abi,splash):
        if path.parent!=ROOT/'build/CASM':raise ValueError('Run outside build/CASM')
        check(path)
    if (abi/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-abi-probe-0.1' or (splash/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-splash-0.1':
        raise ValueError('ABI probe and compact CASM cat required')
    app=OUT/('desktop-usb-'+args.usb if args.usb else 'desktop')
    hashes=json.loads((app/'artifacts.json').read_text())
    for name,digest in hashes.items():
        if hashlib.sha256((app/name).read_bytes()).hexdigest()!=digest:raise ValueError('Stale desktop build: '+name)
    run=ROOT/'build/CASM'/('run-rmlui-media-'+uuid.uuid4().hex[:12]);run.mkdir()
    if args.low_gop:(run/'low-gop.txt').write_text('QEMU VGA preferred 1024x768\n',encoding='ascii')
    if args.usb:(run/'native-usb.txt').write_text(args.usb+'\n',encoding='ascii')
    if args.usb_empty_ports:(run/'native-usb-empty.txt').write_text('QEMU fault test\n',encoding='ascii')
    llvm=Path(os.environ['ProgramFiles'])/'LLVM/bin'
    units=[('allocator','kernel/boot/bridge/desktop_media_alloc.S'),('reader','kernel/boot/bridge/desktop_media_read.S'),
        ('gate','kernel/syscalls/session_gate.S'),('loader','kernel/loader/doom_engine_loader.S')]
    for name,source in units:
        flags=['-DRMLUI_USB','-DDESKTOP_MEDIA','-DXHCI_COMMAND_PROBE'] if args.usb else []
        if args.usb=='both':flags+=['-DXHCI_NATIVE_DUAL']
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-DRMLUI_MEDIA','-DRMLUI_NATIVE','-DDOOM_ENGINE','-DDESKTOP_DOOM',*flags,
            '-c',ROOT/source,'-o',run/(name+'.o')],'compile-media-'+name)
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',run/(name+'.o'),run/(name+'.bin')],'extract-media-'+name)
    sbef=(app/'rmlui.sbef').read_bytes();reference=(abi/'INICIO.X86').read_bytes()
    gate=(run/'gate.bin').read_bytes();loader=(run/'loader.bin').read_bytes()
    packet,_=make_packet(reference,sbef,session_gate=gate,external=loader,engine=True)
    intro=(splash/'INICIO.X86').read_bytes();packet,_=prepend_intro(packet,intro)
    image=bridge_variant(native_ui=True)
    reader=(run/'reader.bin').read_bytes();allocator=(run/'allocator.bin').read_bytes()
    if len(image)!=0x3000 or len(reader)>4096 or len(allocator)>0xf0 or image[0x267:0x26c]!=bytes.fromhex('e894050000'):
        raise ValueError('Native EFI extension exceeds verified slots')
    struct.pack_into('<i',image,0x268,0x3000-0x267-5)
    extra=12288 if args.usb=='both' else 8192 if args.usb else 4096
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
    for case,appfile in [('external-permissions',run/'rejected.sbef'),('normal',run/'rmlui.sbef')]:
        command([sys.executable,scripts/'prepare.py','--workspace',run,'--bmo-x2-folder','--desktop',appfile,'--native-ui'],'prepare-ui-'+case)
        if case!='normal':(run/'build/puente-normal.img').replace(run/'build/puente-external-permissions.img')
    command([sys.executable,scripts/'probe.py','--workspace',run,'--halt','--abi-probe','--doom-fixture',
        '--ram-mib','1024','--casos','normal','external-permissions'],'qemu-fat32-desktop',cwd=run)
    report=json.loads((run/'build/puente-test-results.json').read_text())
    if report['Passed']!=2 or not report['Cases'][0].get('BootLogFat32Verified'):raise ValueError('Missing disk evidence')
    fs=Fat32(run/'build/puente-normal.img')
    try:
        if fs.file_bytes('BMO-X2/DESKTOP/DESKTOP.SBF')!=sbef or fs.file_bytes('BMO-X2/DESKTOP/INICIO.X86',4096)!=packet:
            raise ValueError('FAT32 staged bytes differ')
    finally:fs.close()
    media=run/'media'
    staged={'EFI/BMO-X2/DESKTOP.EFI':image,'BMO-X2/DESKTOP/INICIO.X86':packet,'BMO-X2/DESKTOP/DESKTOP.SBF':sbef}
    for name,data in staged.items():
        target=media/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report.update(run=run.name,evidence='QEMU',disk_sbef=True,physical_boot=False,physical_usb_proven=False,
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
