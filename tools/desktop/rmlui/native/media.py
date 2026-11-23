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

def check_context_stage(llvm, obj, name, budget=2048):
    symbols=subprocess.check_output([llvm/'llvm-nm.exe','--format=posix',obj],text=True)
    positions={fields[0]:int(fields[2],16) for line in symbols.splitlines()
               if len(fields:=line.split())>=3 and fields[0] in (name+'_begin',name+'_end')}
    if not 0<positions[name+'_end']-positions[name+'_begin']<=budget:
        raise ValueError('Context code stage exceeds its reserved region: '+name)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('abi_run',type=Path);p.add_argument('splash_run',type=Path)
    p.add_argument('--low-gop',action='store_true')
    p.add_argument('--msvc-panel',action='store_true',help='Use the optional MSVC desktop build')
    p.add_argument('--usb',choices=['keyboard','mouse','both'],help='Mediated xHCI profile; both uses the dynamic USB2 root transport')
    p.add_argument('--usb-empty-ports',action='store_true',help='QEMU rejection test; never a metal candidate')
    p.add_argument('--nvidia-probe', action='store_true', help='Read PCI display inventory before ExitBootServices')
    p.add_argument('--nvidia-gsp-sample', action='store_true', help='Read the GA106 GSP and SEC2 boot state')
    p.add_argument('--nvidia-gsp-stage', type=Path, help='Directory of the original NVIDIA 615.78.08 files')
    p.add_argument('--nvidia-gsp-prepare', action='store_true', help='Prepare the NVIDIA firmware and detached DMA tree in Ring 0')
    p.add_argument('--nvidia-fwsec-vbios', type=Path, help='Pin FWSEC preparation to the verified MSI GA106 VBIOS')
    p.add_argument('--amdvi-probe', action='store_true', help='Add read-only AMD-Vi firmware inventory')
    p.add_argument('--amdvi-dte-reserve', action='store_true', help='QEMU-only: reserve and verify the full zeroed 2 MiB AMD-Vi DTE table without enabling the IOMMU')
    p.add_argument('--metal-amdvi-preflight', action='store_true',
                   help='Build a separately named METAL preflight candidate; AMD-Vi translation, RTX DMA, GSP and 3D remain disabled')
    p.add_argument('--amdvi-post', action='store_true', help='Take a second AMD-Vi snapshot after ExitBootServices')
    p.add_argument('--amdvi-coexist', action='store_true', help='Exercise virtual EDU and USB DMA together in QEMU')
    p.add_argument('--amdvi-guest-dma', action='store_true', help='Let the guest program AMD-Vi in the virtual lab')
    p.add_argument('--amdvi-storage', action='store_true', help='Read a virtual AHCI disk in a third guest-managed domain')
    p.add_argument('--amdvi-nvme', action='store_true', help='Recover a virtual NVMe namespace in a fourth domain')
    p.add_argument('--amdvi-guest-nvme', action='store_true', help='Let Ring 0 program the fixed NVMe read in QEMU')
    p.add_argument('--amdvi-guest-ahci', action='store_true', help='Let Ring 0 program both fixed disk reads in QEMU')
    p.add_argument('--amdvi-gsp-dma', action='store_true', help='QEMU only: grant and revoke the prepared firmware to EDU alongside USB, AHCI and NVMe')
    p.add_argument('--amdvi-routed', action='store_true', help='Exercise a high PCI requester ID behind a PCIe root port')
    p.add_argument('--dma-census', action='store_true', help='Capture PCI bus masters after USB startup')
    p.add_argument('--storage-state', action='store_true', help='Observe AHCI and NVMe state immediately after UEFI handoff')
    p.add_argument('--storage-quiesce', action='store_true', help='Stop emulated AHCI and NVMe after EBS (QEMU only)')
    p.add_argument('--storage-quiesce-metal', action='store_true', help='Test the measured AMD board storage handoff before DMA activation')
    p.add_argument('--full-hd', action='store_true', help='Render the desktop at native 1920x1080 for GOP')
    args=p.parse_args()
    if args.usb_empty_ports and args.usb!='both':p.error('--usb-empty-ports requires --usb both')
    if args.nvidia_gsp_sample and (not args.nvidia_probe or not args.full_hd):
        p.error('--nvidia-gsp-sample requires the NVIDIA Full HD profile')
    if args.amdvi_gsp_dma and not (args.amdvi_guest_ahci and args.nvidia_probe and args.nvidia_gsp_prepare):
        p.error('--amdvi-gsp-dma requires both guest disk readers and the prepared NVIDIA file')
    if args.nvidia_gsp_stage and ((not args.nvidia_gsp_sample and not args.amdvi_gsp_dma) or args.storage_quiesce):
        p.error('--nvidia-gsp-stage requires the NVIDIA sample on the deployable Full HD profile')
    if args.nvidia_gsp_prepare and (not args.nvidia_gsp_stage or (args.amdvi_coexist and not args.amdvi_gsp_dma)):
        p.error('--nvidia-gsp-prepare requires --nvidia-gsp-stage and a compatible AMD-Vi profile')
    if args.nvidia_fwsec_vbios and not (args.nvidia_gsp_prepare and args.nvidia_gsp_sample):
        p.error('--nvidia-fwsec-vbios requires the sampled NVIDIA profile and --nvidia-gsp-prepare')
    if args.amdvi_post and (not args.amdvi_probe or args.usb!='both' or args.msvc_panel or args.usb_empty_ports):
        p.error('--amdvi-post requires --amdvi-probe with USB both')
    if args.amdvi_dte_reserve and not args.amdvi_probe:
        p.error('--amdvi-dte-reserve requires --amdvi-probe')
    if args.amdvi_dte_reserve and (not args.amdvi_post or args.usb!='both'):
        p.error('--amdvi-dte-reserve requires --amdvi-post and --usb both for post-EBS verification')
    if args.amdvi_coexist and not args.amdvi_post:p.error('--amdvi-coexist requires --amdvi-post')
    if args.amdvi_guest_dma and not args.amdvi_coexist:p.error('--amdvi-guest-dma requires --amdvi-coexist')
    if args.amdvi_storage and not args.amdvi_guest_dma:p.error('--amdvi-storage requires --amdvi-guest-dma')
    if args.amdvi_routed and not args.amdvi_storage:p.error('--amdvi-routed requires --amdvi-storage')
    if args.amdvi_nvme and (not args.amdvi_storage or (args.amdvi_routed and not args.amdvi_gsp_dma)):
        p.error('--amdvi-nvme requires --amdvi-storage; the routed variant also requires --amdvi-gsp-dma')
    if args.amdvi_guest_nvme and not args.amdvi_nvme:
        p.error('--amdvi-guest-nvme requires --amdvi-nvme')
    if args.amdvi_guest_ahci and not args.amdvi_guest_nvme:
        p.error('--amdvi-guest-ahci requires --amdvi-guest-nvme')
    if args.dma_census and (not args.amdvi_post or args.amdvi_coexist):
        p.error('--dma-census requires --amdvi-post and its own context stage')
    if args.storage_state and not args.dma_census:p.error('--storage-state requires --dma-census')
    if args.full_hd and (not args.storage_state or args.low_gop):
        p.error('--full-hd requires --storage-state and its own QEMU display mode')
    if args.metal_amdvi_preflight:
        required = (args.nvidia_probe and args.amdvi_probe and args.amdvi_post and
                    args.amdvi_dte_reserve and args.usb == 'both')
        prohibited = (args.nvidia_gsp_sample or args.nvidia_gsp_stage or args.nvidia_gsp_prepare or
                      args.amdvi_coexist or args.amdvi_guest_dma or args.amdvi_storage or
                      args.amdvi_routed or args.amdvi_nvme or args.amdvi_guest_nvme or
                      args.amdvi_guest_ahci or args.amdvi_gsp_dma or args.dma_census or
                      args.storage_state or args.full_hd or args.storage_quiesce or
                      args.storage_quiesce_metal or args.usb_empty_ports or args.msvc_panel or args.low_gop)
        if not required or prohibited:
            p.error('--metal-amdvi-preflight requires NVIDIA/AMD-Vi probes, post-EBS DTE reserve and USB both; it forbids DMA/GSP/census/storage/guest/quiesce modes')
    if args.storage_quiesce and not args.full_hd:
        p.error('--storage-quiesce uses the combined platform stage of --full-hd')
    if args.storage_quiesce_metal and not (args.full_hd and args.nvidia_fwsec_vbios and not args.storage_quiesce):
        p.error('--storage-quiesce-metal requires the measured NVIDIA FWSEC Full HD profile')
    storage_handoff = args.storage_quiesce or args.storage_quiesce_metal
    abi,splash=args.abi_run.resolve(),args.splash_run.resolve()
    for path in (abi,splash):
        if path.parent!=ROOT/'build/CASM':raise ValueError('Run outside build/CASM')
        check(path)
    if (abi/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-abi-probe-0.1' or (splash/'profile.txt').read_text(encoding='utf-8-sig').strip()!='ring0-splash-0.1':
        raise ValueError('ABI probe and compact CASM cat required')
    variant='desktop-usb-'+args.usb if args.usb else 'desktop'
    if args.amdvi_post:variant+='-amdvi-post'
    if args.amdvi_dte_reserve:variant+='-amdvi-dte-report'
    if args.dma_census:variant+='-dma-census'
    if args.storage_state:variant+='-storage-state'
    if args.full_hd:variant+='-full-hd'
    app=OUT/(variant + ('-msvc' if args.msvc_panel else ''))
    hashes=json.loads((app/'artifacts.json').read_text())
    for name,digest in hashes.items():
        if hashlib.sha256((app/name).read_bytes()).hexdigest()!=digest:raise ValueError('Stale desktop build: '+name)
    run=ROOT/'build/CASM'/('run-rmlui-media-'+uuid.uuid4().hex[:12]);run.mkdir()
    gsp = None
    nvidia_reader_flags = []
    if args.nvidia_gsp_stage:
        from host.gpu.NVIDIA.bundle import stage_firmware

        gsp,nvidia_reader_flags = stage_firmware(run,args.nvidia_gsp_stage,args.nvidia_gsp_prepare,args.nvidia_fwsec_vbios)
    (run/'gop-regions.txt').write_text('cpu-gop\n',encoding='ascii')
    if args.nvidia_probe:
        (run/'nvidia-pci-probe.txt').write_text('pci-read-only\n', encoding='ascii')
    if args.metal_amdvi_preflight:
        (run/'gpu-preflight.txt').write_text('read-only-gpu-preflight\n', encoding='ascii')
    if args.nvidia_gsp_sample:
        (run/'nvidia-gsp-sample.txt').write_text('ga106-gsp-wpr-read-only\n', encoding='ascii')
    if args.amdvi_probe:
        (run/'amdvi-efi-probe.txt').write_text('firmware-read-only\n', encoding='ascii')
    if args.amdvi_dte_reserve:
        (run/'amdvi-dte-reserve.txt').write_text('qemu-only-512-page-zeroed-table\n', encoding='ascii')
    if args.amdvi_post:
        (run/'amdvi-post-probe.txt').write_text('post-ebs-read-only\n', encoding='ascii')
    if args.dma_census:
        (run/'dma-census-probe.txt').write_text('pci-segment0-bme\n', encoding='ascii')
    if args.storage_state:
        (run/'storage-state.txt').write_text('post-ebs-read-only\n', encoding='ascii')
    if args.storage_quiesce:
        (run/'storage-quiesce.txt').write_text('qemu-only-ahci-nvme-shutdown\n', encoding='ascii')
    if args.storage_quiesce_metal:
        (run/'storage-quiesce-metal.txt').write_text('board-matched-ahci-nvme-shutdown\n', encoding='ascii')
    if args.full_hd:
        (run/'full-hd.txt').write_text('cpu-gop-native-1920x1080\n', encoding='ascii')
    if args.amdvi_coexist:
        (run/'amdvi-coexist-probe.txt').write_text('qemu-only-edu-xhci\n', encoding='ascii')
    if args.amdvi_guest_dma:
        (run/'amdvi-guest-dma.txt').write_text('qemu-only-guest-iommu\n', encoding='ascii')
    if args.amdvi_storage:
        (run/'amdvi-storage.txt').write_text('qemu-only-ahci-read\n', encoding='ascii')
    if args.amdvi_routed:
        (run/'amdvi-routed.txt').write_text('qemu-only-high-pci-requester\n', encoding='ascii')
    if args.amdvi_nvme:
        (run/'amdvi-nvme.txt').write_text('qemu-only-nvme-queues\n', encoding='ascii')
    if args.amdvi_guest_nvme:
        (run/'amdvi-guest-nvme.txt').write_text('qemu-only-nvme-queues-ring0\n', encoding='ascii')
    if args.amdvi_guest_ahci:
        (run/'amdvi-guest-ahci.txt').write_text('qemu-only-ahci-commands-ring0\n', encoding='ascii')
    if args.amdvi_gsp_dma:
        (run/'amdvi-gsp-dma.txt').write_text('qemu-only-prepared-firmware\n', encoding='ascii')
    if args.low_gop:(run/'low-gop.txt').write_text('QEMU VGA preferred 1024x768\n',encoding='ascii')
    if args.usb:(run/'native-usb.txt').write_text(args.usb+'\n',encoding='ascii')
    if args.usb_empty_ports:(run/'native-usb-empty.txt').write_text('QEMU fault test\n',encoding='ascii')
    llvm=Path(os.environ['ProgramFiles'])/'LLVM/bin'
    # The GPU + AMD-Vi read-only profile adds a second reader page. Keep the
    # xHCI and AMD-Vi blobs page-aligned after that larger reader.
    reader_budget=8192 if args.metal_amdvi_preflight else 4096
    usb_budget=8192 if args.usb=='both' else 4096 if args.usb else 0
    extra=reader_budget+usb_budget
    amdvi_offset=0x3000+extra
    amdvi_budget=8192 if args.full_hd or args.amdvi_guest_nvme or (args.amdvi_routed and args.amdvi_dte_reserve) else 4096
    gsp_offset=amdvi_offset+amdvi_budget
    units=[('allocator','kernel/boot/bridge/desktop_media_alloc.S'),('reader','kernel/boot/bridge/desktop_media_read.S'),
        ('gate','kernel/syscalls/session_gate.S'),('loader','kernel/loader/doom_engine_loader.S')]
    for name,source in units:
        flags=['-DRMLUI_USB','-DDESKTOP_MEDIA','-DXHCI_COMMAND_PROBE'] if args.usb else []
        if args.metal_amdvi_preflight and name=='reader':flags+=['-DBMO_EXTENDED_MEDIA_READER','-DBMO_GPU_PREFLIGHT']
        if args.amdvi_gsp_dma:flags+=['-DBMO_AMDVI_GSP_DMA']
        if args.usb=='both':flags+=['-DXHCI_NATIVE_DUAL']
        if args.nvidia_probe and name == 'reader':flags+=['-DBMO_NVIDIA_PCI_PROBE']
        if args.nvidia_gsp_sample and name == 'reader':flags+=['-DBMO_NVIDIA_GSP_SAMPLE']
        if name=='reader':flags+=nvidia_reader_flags
        if args.nvidia_gsp_prepare and name=='reader':flags+=[f'-DBMO_GSP_PREPARE_OFFSET={gsp_offset}']
        if args.nvidia_gsp_prepare and name=='loader':flags+=['-DBMO_NVIDIA_GSP_PREPARE']
        if args.nvidia_gsp_prepare and name=='gate':flags+=['-DBMO_NVIDIA_GSP_STATUS']
        if args.amdvi_probe and name == 'reader':flags+=[f'-DBMO_AMDVI_EFI_OFFSET={amdvi_offset}']
        if args.amdvi_dte_reserve and name == 'reader':flags+=['-DBMO_AMDVI_DTE_RESERVE']
        if args.amdvi_post and name in ('reader','gate'):flags+=['-DBMO_AMDVI_POST']
        if args.dma_census and name=='gate':flags+=['-DBMO_DMA_CENSUS']
        if args.amdvi_guest_dma and name=='gate':flags+=['-DBMO_AMDVI_GUEST_DMA']
        if args.amdvi_storage and name in ('reader','gate'):flags+=['-DBMO_AMDVI_STORAGE']
        if args.full_hd and name in ('allocator','reader','loader'):flags+=['-DBMO_FULL_HD']
        if storage_handoff and name=='gate':flags+=['-DBMO_STORAGE_QUIESCE']
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-DRMLUI_MEDIA','-DRMLUI_NATIVE',
            '-DRMLUI_GOP_REGIONS','-DDOOM_ENGINE','-DDESKTOP_DOOM',*flags,
            '-c',ROOT/source,'-o',run/(name+'.o')],'compile-media-'+name)
        if args.amdvi_post and name=='reader' and not (args.full_hd or args.amdvi_gsp_dma):
            check_context_stage(llvm,run/'reader.o','gop_stage',1536 if args.amdvi_storage else 2048)
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',run/(name+'.o'),run/(name+'.bin')],'extract-media-'+name)
    sbef=(app/'rmlui.sbef').read_bytes();reference=(abi/'INICIO.X86').read_bytes()
    gate=(run/'gate.bin').read_bytes();loader=(run/'loader.bin').read_bytes()
    packet,_=make_packet(reference,sbef,session_gate=gate,external=loader,engine=True,full_hd=args.full_hd)
    intro=(splash/'INICIO.X86').read_bytes();packet,_=prepend_intro(packet,intro)
    image=bridge_variant(native_ui=True,nvidia_probe=args.nvidia_probe,
                         gpu_preflight=args.metal_amdvi_preflight)
    reader=(run/'reader.bin').read_bytes();allocator=(run/'allocator.bin').read_bytes()
    if len(image)!=0x3000 or len(reader)>reader_budget or len(allocator)>0xf0 or image[0x267:0x26c]!=bytes.fromhex('e894050000'):
        raise ValueError('Native EFI extension exceeds verified slots')
    struct.pack_into('<i',image,0x268,0x3000-0x267-5)
    if args.amdvi_probe:extra+=amdvi_budget
    if args.nvidia_gsp_prepare:extra+=4096
    for offset,old in ((0x5c,0x2e00),(0x90,0x4000),(0x150,0x2e00),(0x158,0x2e00)):
        if struct.unpack_from('<I',image,offset)[0]!=old:raise ValueError('EFI PE header changed')
        struct.pack_into('<I',image,offset,old+extra)
    image.extend(reader.ljust(reader_budget,b'\0'))
    if args.usb:
        flags=['-DRMLUI_USB']+(['-DXHCI_NATIVE_DUAL'] if args.usb=='both' else ['-DXHCI_COMMAND_PROBE'])+(['-DXHCI_MOUSE_PROBE'] if args.usb=='mouse' else [])
        if args.full_hd:flags+=['-DBMO_FULL_HD']
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-x','assembler-with-cpp',*flags,'-c',
            ROOT/'kernel/drivers/bus/xhci_inventory.inc','-o',run/'xhci.o'],'compile-native-xhci')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',run/'xhci.o',run/'xhci.bin'],'extract-native-xhci')
        stage=(run/'xhci.bin').read_bytes()
        budget=usb_budget
        if not 0<len(stage)<=budget:raise ValueError('USB stage exceeds its explicit reserved code pages')
        image.extend(stage.ljust(budget,b'\0'))
    if args.amdvi_probe:
        source=ROOT/'kernel/drivers/bus/amdvi/firmware_probe.S'
        native_probe=run/'amdvi-firmware.o'
        flags=['-DBMO_AMDVI_POST'] if args.amdvi_post else []
        if args.amdvi_dte_reserve:flags+=['-DBMO_AMDVI_DTE_RESERVE']
        if args.amdvi_coexist:flags+=['-DBMO_AMDVI_COEXIST']
        if args.dma_census:flags+=['-DBMO_DMA_CENSUS']
        if args.storage_state:flags+=['-DBMO_STORAGE_STATE']
        if storage_handoff:flags+=['-DBMO_STORAGE_QUIESCE']
        if args.storage_quiesce_metal:flags+=['-DBMO_STORAGE_QUIESCE_METAL']
        if args.full_hd:flags+=['-DBMO_FULL_HD','-DRMLUI_MEDIA','-DRMLUI_NATIVE','-DDESKTOP_DOOM']
        if args.amdvi_guest_dma:flags+=['-DBMO_AMDVI_GUEST_DMA']
        if args.amdvi_storage:flags+=['-DBMO_AMDVI_STORAGE']
        if args.amdvi_routed:flags+=['-DBMO_AMDVI_ROUTED']
        if args.amdvi_nvme:flags+=['-DBMO_AMDVI_NVME']
        if args.amdvi_guest_nvme:flags+=['-DBMO_AMDVI_GUEST_NVME']
        if args.amdvi_guest_ahci:flags+=['-DBMO_AMDVI_GUEST_AHCI']
        if args.amdvi_gsp_dma:
            flags+=['-DBMO_AMDVI_GSP_DMA','-DRMLUI_MEDIA','-DRMLUI_NATIVE','-DDESKTOP_DOOM',*nvidia_reader_flags]
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf',*flags,'-c',source,'-o',native_probe],'compile-amdvi-firmware')
        if args.amdvi_post:
            post_budget=3168 if args.amdvi_gsp_dma else 3072 if args.amdvi_routed else 2560 if args.amdvi_storage or storage_handoff else 2048
            check_context_stage(llvm,native_probe,'amdvi_post',post_budget)
        if args.full_hd or args.amdvi_gsp_dma:
            gop_budget=928 if args.amdvi_gsp_dma else 1536 if storage_handoff else 2048
            check_context_stage(llvm,native_probe,'gop_stage',gop_budget)
        if args.amdvi_guest_nvme:check_context_stage(llvm,native_probe,'nvme_guest',4096)
        relocations=subprocess.check_output([llvm/'llvm-objdump.exe','-r',native_probe],text=True)
        if 'RELOCATION RECORDS' in relocations:raise ValueError('AMD-Vi firmware inventory must be position independent')
        raw_probe=native_probe.with_suffix('.bin')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',native_probe,raw_probe],'extract-amdvi-firmware')
        stage=raw_probe.read_bytes()
        if len(image)!=amdvi_offset or not 0<len(stage)<=amdvi_budget:raise ValueError('AMD-Vi EFI slot mismatch')
        image.extend(stage.ljust(amdvi_budget,b'\0'))
    if args.nvidia_gsp_prepare:
        source=ROOT/'kernel/drivers/GPU/NVIDIA/gsp_prepare.inc'
        obj=run/'nvidia-gsp-prepare.o'
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-x','assembler-with-cpp',
                 *nvidia_reader_flags,'-c',source,'-o',obj],'compile-nvidia-gsp-prepare')
        check_context_stage(llvm,obj,'gsp_prepare',4096)
        relocations=subprocess.check_output([llvm/'llvm-objdump.exe','-r',obj],text=True)
        if 'RELOCATION RECORDS' in relocations:raise ValueError('NVIDIA stage must be position independent')
        binary=obj.with_suffix('.bin')
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',obj,binary],'extract-nvidia-gsp-prepare')
        stage=binary.read_bytes()
        if len(image)!=gsp_offset or not 0<len(stage)<=4096:raise ValueError('NVIDIA EFI slot mismatch')
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
    prepare_flags = (['--nvidia-probe','--gpu-preflight'] if args.metal_amdvi_preflight else
                     ['--nvidia-probe'] if args.nvidia_probe else [])
    media_cases = [('external-permissions',run/'rejected.sbef')]
    if gsp is not None:
        media_cases.append(('amdvi-missing',run/'rmlui.sbef'))
    media_cases.append(('normal',run/'rmlui.sbef'))
    for case,appfile in media_cases:
        gsp_flags = []
        if gsp is not None and case != 'amdvi-missing':
            gsp_flags = ['--gsp-firmware', run/('GSP.BIN' if case=='normal' else 'corrupted-gsp.bin')]
        case_flags = ['--native-case', case] if case != 'normal' else []
        command([sys.executable,scripts/'prepare.py','--workspace',run,'--bmo-x2-folder','--desktop',appfile,'--native-ui',*prepare_flags,*gsp_flags,*case_flags],'prepare-ui-'+case)
    cases=['normal','external-permissions']+(['amdvi-missing'] if args.amdvi_post else [])
    command([sys.executable,scripts/'probe.py','--workspace',run,'--halt','--abi-probe','--doom-fixture',
        '--ram-mib','1024','--casos',*cases],'qemu-fat32-desktop',cwd=run)
    report=json.loads((run/'build/puente-test-results.json').read_text())
    if report['Passed']!=len(cases) or not report['Cases'][0].get('BootLogFat32Verified'):raise ValueError('Missing disk evidence')
    if args.nvidia_probe and (not report['Cases'][0].get('GpuBar0UefiBytes') or
                             not report['Cases'][0].get('GpuNvidiaMmioSkipped')):
        raise ValueError('Missing UEFI BAR0 bounds or device guard evidence')
    if args.nvidia_gsp_sample and not all(case.get('GpuGspSampleSkipped') for case in report['Cases']):
        raise ValueError('Missing GSP sampling exclusion evidence')
    if args.nvidia_gsp_sample and not all(case.get('GpuWprSampleSkipped') for case in report['Cases']):
        raise ValueError('Missing WPR sampling exclusion evidence')
    if gsp is not None and ([case.get('GspStageStatus') for case in report['Cases']] != [5,4,1] or
                            not report['Cases'][0].get('GspResidentVerified')):
        raise ValueError('Missing GSP staging or file rejection evidence')
    if args.nvidia_gsp_prepare and (not report['Cases'][0].get('GspDetachedDmaVerified') or
                                   not all(report['Cases'][i].get('GspStatusExportVerified') for i in (0,2))):
        raise ValueError('Missing Ring 0 detached DMA tree and Ring 3 status evidence')
    if args.nvidia_gsp_prepare and not report['Cases'][0].get('GspQueuePermissionsVerified'):
        raise ValueError('Missing Ring 0 GSP message queue evidence')
    if args.nvidia_gsp_prepare and not report['Cases'][0].get('GspLibosVerified'):
        raise ValueError('Missing Ring 0 GSP LIBOS argument and log evidence')
    if args.nvidia_gsp_prepare and not report['Cases'][0].get('GspBootChainVerified'):
        raise ValueError('Missing signed GSP boot chain in the detached DMA tree')
    if args.nvidia_gsp_prepare and not report['Cases'][0].get('GspWprPageExcluded'):
        raise ValueError('Missing reserved WPR page exclusion on standard VGA')
    if args.nvidia_fwsec_vbios and not report['Cases'][0].get('GspFwsecExcluded'):
        raise ValueError('Missing FWSEC exclusion on standard VGA')
    if args.amdvi_probe and not all(case.get('AmdViMmioVerified') for case in report['Cases']):
        raise ValueError('Missing AMD-Vi MMIO evidence')
    if args.amdvi_post and not all(report['Cases'][i].get('AmdViPostVerified') for i in (0,2)):
        raise ValueError('Missing post-EBS AMD-Vi evidence')
    if args.amdvi_dte_reserve and not report['Cases'][0].get('AmdViDtePostReadVerified'):
        raise ValueError('Missing post-EBS DTE read and alias-revocation evidence')
    if args.dma_census and (not all(report['Cases'][i].get('DmaCensusVerified') for i in (0,2)) or
                            (not args.storage_quiesce and not report['Cases'][0].get('DmaCensusPanelVerified'))):
        raise ValueError('Missing PCI DMA inventory or its Ring 3 panel evidence')
    if args.storage_state and (not all(report['Cases'][i].get('StorageStateVerified') for i in (0,2)) or
                               (not args.storage_quiesce and not report['Cases'][0].get('StoragePanelVerified'))):
        raise ValueError('Missing storage state or its Ring 3 panel evidence')
    if args.storage_quiesce_metal and not all(report['Cases'][i].get('StorageQuiesceSkippedVerified') for i in (0,2)):
        raise ValueError('The board-specific shutdown was not excluded in QEMU')
    if args.storage_quiesce and (not report['Cases'][0].get('StorageQuiesceVerified') or
                                 not report['Cases'][0].get('StorageQuiesceHidVerified') or
                                 not report['Cases'][2].get('StorageQuiesceSkippedVerified')):
        raise ValueError('Missing shutdown, HID or fail-closed evidence')
    if args.full_hd and (not report['Cases'][0].get('FullHdNativeRasterVerified') or
                         not report['Cases'][2].get('FullHdFallbackVerified')):
        raise ValueError('Missing 1080p scanout or desktop fallback evidence')
    if args.amdvi_coexist and not report['Cases'][0].get('AmdViCoexistVerified'):
        raise ValueError('Missing simultaneous EDU and USB evidence')
    if args.amdvi_guest_dma and report['Cases'][0].get('DmaIssuer')!='Ring 0 guest':
        raise ValueError('Missing guest-owned AMD-Vi evidence')
    if args.amdvi_storage and not report['Cases'][0].get('AhciTranslatedReadsVerified'):
        raise ValueError('Missing translated AHCI reads')
    if args.amdvi_nvme and not report['Cases'][0].get('NvmeTranslatedReadsVerified'):
        raise ValueError('Missing translated NVMe reads')
    if args.amdvi_guest_nvme and report['Cases'][0].get('NvmeQueueOwner')!='Ring 0 guest':
        raise ValueError('Missing guest-owned NVMe queues')
    if args.amdvi_guest_ahci and (report['Cases'][0].get('AhciQueueOwner')!='Ring 0 guest' or
                                 not report['Cases'][0].get('GuestStorageHandoff')):
        raise ValueError('Missing guest-owned storage handoff and AHCI commands')
    if args.amdvi_gsp_dma and not all(report['Cases'][0].get(field) for field in
                                     ('GspDmaCoexistenceVerified','GspStatusQueueDmaWriteVerified',
                                      'GspRmargsDmaWriteDenied','GspLibosArgumentWriteDenied',
                                      'GspLibosLogWriteVerified','GspBootChainReadVerified',
                                      'GspBootChainWriteDenied')):
        raise ValueError('Missing prepared firmware DMA grant and revocation evidence')
    if args.amdvi_gsp_dma and args.amdvi_routed and not report['Cases'][0].get('GspSiblingDmaDenied'):
        raise ValueError('Missing isolation evidence for PCI function 29:00.1')
    if args.amdvi_gsp_dma and not all(report['Cases'][0].get(field) for field in (
        'GspBusMasterGrantedByRing0','GspBusMasterClosedByRing0','GspDteThenDomainInvalidationVerified',
        'GspReopenRejected','GspIncompleteRevocationClosedAndPinned',
    )):
        raise ValueError('Missing Ring 0 graphics DMA grant and closed revocation')
    if args.amdvi_routed and (not report['Cases'][0].get('RoutedDmaVerified') or
                             not report['Cases'][0].get('UnassignedRequesterBlocked')):
        raise ValueError('Missing translated DMA or default-deny evidence')
    if args.amdvi_routed and report['Cases'][0].get('DeviceTablePages')!=512:
        raise ValueError('The routed QEMU domain does not cover all 65536 requester IDs')
    media_prefix = ('BMO-X2/GPU-PF' if args.metal_amdvi_preflight else
                    'BMO-X2/GPU' if args.nvidia_probe else 'BMO-X2/DESKTOP')
    fs=Fat32(run/'build/puente-normal.img')
    try:
        if fs.file_bytes(f'{media_prefix}/DESKTOP.SBF')!=sbef or fs.file_bytes(f'{media_prefix}/INICIO.X86',4096)!=packet:
            raise ValueError('FAT32 staged bytes differ')
        if gsp is not None and fs.file_bytes(f'{media_prefix}/GSP.BIN',len(gsp))!=gsp:
            raise ValueError('FAT32 GSP container differs')
    finally:fs.close()
    media=run/'media'
    boot_name = ('AMDVI-PREFLIGHT.EFI' if args.metal_amdvi_preflight else
                 'NVIDIA.EFI' if args.nvidia_probe else 'DESKTOP.EFI')
    staged={f'EFI/BMO-X2/{boot_name}':image,f'{media_prefix}/INICIO.X86':packet,f'{media_prefix}/DESKTOP.SBF':sbef}
    if gsp is not None:
        staged[f'{media_prefix}/GSP.BIN'] = gsp
    storage_lab_only = (args.storage_quiesce or args.amdvi_nvme or args.amdvi_dte_reserve or
                        args.amdvi_routed) and not args.metal_amdvi_preflight
    if not storage_lab_only:
        for name,data in staged.items():
            target=media/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    report.update(run=run.name,evidence='QEMU',disk_sbef=True,physical_boot=False,physical_usb_proven=False,
        display_backend='cpu-gop',
        nvidia_pci_probe=args.nvidia_probe, amdvi_efi_probe=args.amdvi_probe, amdvi_mmio_probe=args.amdvi_probe,
        nvidia_gsp_sample=args.nvidia_gsp_sample,
        nvidia_wpr_sample=args.nvidia_gsp_sample,
        nvidia_gsp_stage=gsp is not None,
        nvidia_gsp_prepare=args.nvidia_gsp_prepare,
        amdvi_post_probe=args.amdvi_post,
        dma_census=args.dma_census,
        storage_state=args.storage_state,
        storage_quiesce=args.storage_quiesce,
        storage_quiesce_metal=args.storage_quiesce_metal,
        full_hd=args.full_hd,
        full_hd_native=args.full_hd,
        amdvi_coexist=args.amdvi_coexist,
        amdvi_guest_dma=args.amdvi_guest_dma,
        amdvi_storage=args.amdvi_storage,
        amdvi_routed=args.amdvi_routed,
        amdvi_nvme=args.amdvi_nvme,
        amdvi_guest_nvme=args.amdvi_guest_nvme,
        amdvi_guest_ahci=args.amdvi_guest_ahci,
        amdvi_gsp_dma=args.amdvi_gsp_dma,
        amdvi_dte_reserve=args.amdvi_dte_reserve,
        qemu_only=(bool(args.usb) or args.amdvi_dte_reserve) and not args.metal_amdvi_preflight,
        metal_amdvi_preflight=args.metal_amdvi_preflight,
        physical_dma_translation_enabled=False,
        nvidia_dma_grant=False,
        nvidia_gsp_verified=False,
        native_gpu_3d_verified=False,
        usb_profile=args.usb,
        usb_empty_ports=args.usb_empty_ports,
        hardware_profile='amd149c-usb2-root-experimental' if args.usb=='both' and not args.usb_empty_ports else None,
        note=('QEMU-only lab; no installable media is emitted.' if storage_lab_only else
              'METAL preflight only: fresh PCI/AMD-Vi snapshots and DTE reservation/readback; translation and RTX DMA stay disabled, no GSP or native 3D.' if args.metal_amdvi_preflight else
              'Separate desktop candidate; no QEMU loader device, UEFI reads real FAT32 files.'),
        files={} if storage_lab_only else {name:hashlib.sha256(data).hexdigest() for name,data in staged.items()})
    (run/'qemu-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    (run/'qemu-run.json').write_text(json.dumps(dict(cpu='qemu64',ram_mib=1024))+'\n',encoding='ascii')
    if storage_lab_only:
        print('Verified QEMU storage lab: '+str(run))
    else:
        (media/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
        print('Verified candidate: '+str(media))

if __name__=='__main__':main()
