"""Link the actual C++ engine and Rust CPU backend into a native UI executable."""
import json
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import struct
import sys
from build import ROOT, OUT, DEPS, generate_headers, command, write_if_changed
import libc


def check_sections(elf):
    offset=struct.unpack_from('<Q',elf,40)[0]
    size,count=struct.unpack_from('<HH',elf,58)
    if size!=64 or offset+size*count>len(elf):raise ValueError('Native section table')
    for i in range(count):
        flags,address,_,length=struct.unpack_from('<QQQQ',elf,offset+i*size+8)
        if flags&2:
            if flags&4 and not 0x40000000<=address<=address+length<=0x40200000:
                raise ValueError('Executable native section outside RX')
            # Statically relocated init_array inputs carry SHF_WRITE, but their
            # output is deliberately in the R-only PT_LOAD. The SBEF importer
            # validates program permissions; executable code must be in RX.


def check_math_providers(text):
    names={'cosf','sinf','sqrtf','floorf','ceilf','powf','atan2f','acosf','asinf','tanf','expf','fmodf','modff','floor'}
    for line in text.splitlines():
        fields=line.split('\t')
        if len(fields)==3 and fields[2] in names and 'libbmo-compute.a(' not in fields[1]:
            raise ValueError('Wrong floating-point ABI provider for '+fields[2]+': '+fields[1])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop',action='store_true')
    parser.add_argument('--msvc-panel-cc', help='Optional cl.exe for the trusted Win64 panel')
    parser.add_argument('--usb',choices=['keyboard','mouse','both'])
    parser.add_argument('--amdvi-post',action='store_true')
    parser.add_argument('--dma-census',action='store_true')
    parser.add_argument('--storage-state',action='store_true')
    args=parser.parse_args()
    if args.usb and not args.desktop:parser.error('--usb requires --desktop')
    if args.msvc_panel_cc and not args.desktop:parser.error('--msvc-panel-cc requires --desktop')
    if args.amdvi_post and (not args.desktop or args.usb!='both' or args.msvc_panel_cc):
        parser.error('--amdvi-post requires the desktop with USB both')
    if args.dma_census and not args.amdvi_post:
        parser.error('--dma-census requires --amdvi-post')
    if args.storage_state and not args.dma_census:
        parser.error('--storage-state requires --dma-census')
    libc.main()
    here=Path(__file__).parent
    llvm=Path(os.environ['ProgramFiles'])/'LLVM/bin'
    variant='desktop-usb-'+args.usb if args.usb else 'desktop' if args.desktop else 'guest'
    if args.amdvi_post:variant+='-amdvi-post'
    if args.dma_census:variant+='-dma-census'
    if args.storage_state:variant+='-storage-state'
    out=OUT/(variant + ('-msvc' if args.msvc_panel_cc else ''))
    out.mkdir(exist_ok=True)
    includes=generate_headers()
    flags=['--target=x86_64-unknown-none-elf','-Os','-ffreestanding','-fno-builtin',
        '-fno-stack-protector','-fno-pic','-fno-pie','-mno-red-zone','-ffunction-sections',
        '-fdata-sections','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
        '-D_POSIX_C_SOURCE=200809L']
    cflags=flags+['-I'+str(p) for p in [DEPS/'musl-1.2.5/src/include',DEPS/'musl-1.2.5/src/internal',*includes,ROOT/'tools/doom']]
    for unit in ('arena','services'):
        command([llvm/'clang.exe',*cflags,'-c',here/(unit+'.c'),'-o',out/(unit+'.o')],'compile-'+unit)
    cppflags=flags+['-std=c++17','-nostdinc++','-fno-exceptions','-fno-rtti','-fno-threadsafe-statics',
        '-fno-use-cxa-atexit','-DBMO_UI_NATIVE','-DRMLUI_STATIC_LIB','-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE']
    cppflags+=['-I'+str(p) for p in [OUT/'runtime/include/c++/v1',*includes,DEPS/'RmlUi-6.3/Include',ROOT/'tools/doom']]
    if args.desktop:cppflags+=['-DBMO_DESKTOP_UI']
    if args.usb:cppflags+=['-DBMO_USB_INPUT']+(['-DBMO_USB_MOUSE'] if args.usb=='mouse' else [])
    if args.usb=='both':cppflags+=['-DBMO_USB_DUAL']
    if args.msvc_panel_cc:cppflags+=['-DBMO_MSVC_PANEL']
    if args.amdvi_post:cppflags+=['-DBMO_AMDVI_POST']
    if args.dma_census:cppflags+=['-DBMO_DMA_CENSUS']
    if args.storage_state:cppflags+=['-DBMO_STORAGE_STATE']
    command([llvm/'clang++.exe',*cppflags,'-c',here/'guest.cpp','-o',out/'guest.o'],'compile-native-guest')
    command([llvm/'clang++.exe',*cppflags,'-c',here/'new.cpp','-o',out/'new.o'],'compile-native-new')
    rust_extra=[]
    if args.desktop:
        command(['rustc','--edition=2024','--target=x86_64-unknown-none','--crate-type=rlib','--crate-name=bmo_director','--cfg','bmo_embedded','-Cpanic=abort',
            '-Copt-level=z','-Crelocation-model=static','-Cforce-unwind-tables=no',
            ROOT/'userspace/services/desktop/src/native_policy.rs','-o',out/'libdirector.rlib'],'compile-native-director')
        rust_extra=['--extern','bmo_director='+str(out/'libdirector.rlib'),'--cfg','native_desktop']
    if args.usb:
        command(['rustc','--edition=2024','--target=x86_64-unknown-none','--crate-type=rlib','--crate-name=bmo_x2_usb','-Dwarnings','-Cpanic=abort',
            '-Copt-level=z','-Crelocation-model=static',ROOT/'userspace/drivers/usb/src/lib.rs','-o',out/'libusb.rlib'],'compile-native-usb')
        rust_extra+=['--extern','bmo_x2_usb='+str(out/'libusb.rlib'),'--cfg','native_usb']
    command(['rustc','--edition=2024','--target=x86_64-unknown-none','--crate-type=staticlib','-Cpanic=abort',
        '-Copt-level=z','-Crelocation-model=static','-Cforce-unwind-tables=no',*rust_extra,
        here.parent/'raster.rs','-o',out/'libraster.a'],'compile-native-rust')
    assets=ROOT/'Ultra-J/examples/rmlui-desktop'
    text=(assets/'main.rml').read_text().replace('Prueba en HOST.','Motor nativo en Ring 3.').replace('HOST PREVIEW','RING 3 / CPU').replace('VISTA HOST / DIBUJO CPU / SIN CAMBIOS EN EL BOOT','SBEF NATIVO / DIBUJO CPU / RMLUI + ULTRA-J')
    if args.desktop:
        text=text.replace('<div class="nav">02 <span>Aplicaciones</span></div>',
            '<button id="open-app" class="nav" style="width:175px;box-sizing:border-box;margin:0 0 8px;padding:0 14px;text-align:left;font-weight:normal;background:#1a2f39;color:#7de3d2;">02 Abrir ULTRA-J</button>')
        text=text.replace('<body>', '<body class="native-desktop">')
        bar=('<span id="desktop-status" class="muted">Espacio 1</span>'
            '<div id="space-strip" aria-label="Espacios de trabajo">'
            + ''.join(f'<span id="space-{n}" class="key-chip">{n}</span>' for n in range(1,5))
            + '</div><div id="lock-strip" aria-label="Bloqueos del teclado">'
            '<span id="lock-num" class="key-chip">NUM</span><span id="lock-caps" class="key-chip">MAYUS</span>'
            '<span id="lock-scroll" class="key-chip">DESPL</span></div>')
        text=text.replace('<span class="muted">BMO-X2 / DIRECTOR</span>',bar)
        text=text.replace('HECHO PARA CRECER','CTRL+SUPER+1..4 / SUPER+Q')
    if args.amdvi_post:
        text=text.replace('<span class="footer-note">SBEF NATIVO / DIBUJO CPU / RMLUI + ULTRA-J</span>',
                          '<div id="amdvi-post" style="color:#d7fff6;font-size:13px;letter-spacing:0;"></div>')
    if args.dma_census:
        text=text.replace('CTRL+SUPER+1..4 / SUPER+Q','CTRL+SUPER+1..4 / SUPER+Q / F2 PCI')
        text=text.replace('<div id="bottom">','<div id="dma-census" style="display:none;position:absolute;'
            'left:246px;right:36px;top:115px;height:515px;padding:24px;'
            'background:#101c29;border:1px #658e98;z-index:10;"></div><div id="bottom">')
    if args.msvc_panel_cc:
        text=text.replace('<div class="nav">03 <span>Archivos</span></div>',
            '<button id="open-msvc" class="nav">Abrir panel MSVC</button>')
        text=text.replace('<div id="bottom">', '<div id="msvc-panel" style="display:none;">'
            '<h2>Hola ventana</h2><p class="description">C++ / MSVC</p>'
            '<div id="msvc-surface"></div></div><div id="bottom">')
    write_if_changed(out/'main.rml',text)
    paths=[out/'main.rml',assets/'style.rcss',DEPS/'RmlUi-6.3/Samples/assets/LatoLatin-Regular.ttf',DEPS/'RmlUi-6.3/Samples/assets/LatoLatin-Bold.ttf']
    asm='.section .rodata\n'
    for i,p in enumerate(paths):
        asm+=f'.globl resource_{i},resource_{i}_end\nresource_{i}:\n.incbin "{p.as_posix()}"\nresource_{i}_end:\n'
    if args.msvc_panel_cc:
        sys.path.insert(0,str(ROOT/'tools'))
        from host.toolchains.msvc import build_desktop_panel
        panel=build_desktop_panel(ROOT,out,args.msvc_panel_cc,llvm/'llvm-nm.exe')
        asm+=f'.section .text.msvc_panel,"ax",@progbits\n.balign 16\n.globl bmo_msvc_panel\nbmo_msvc_panel:\n.incbin "{panel.as_posix()}"\n.section .rodata\n'
    sys.path.insert(0,str(ROOT/'Ultra-J'))
    from compiler import compile_source
    action=compile_source((assets/'main.uj').read_bytes())
    (out/'action.ujb').write_bytes(action)
    asm+=f'.globl bmo_action_blob\nbmo_action_blob:\n.quad {len(action)}\n.incbin "{(out/"action.ujb").as_posix()}"\n'
    write_if_changed(out/'assets.S',asm)
    vm=(ROOT/'Ultra-J/targets/x86_64/action_vm.inc').read_text()
    old='    mov $0x40003df8, %esi'
    if vm.count(old)!=1:raise ValueError('Review action VM resource address')
    vm=vm.replace(old,'    lea bmo_action_blob(%rip), %rsi')
    write_if_changed(out/'action.S','.text\n.globl bmo_uj_action\nbmo_uj_action:\n'+vm+'\ninvalid:\n xor %eax,%eax\n ret\n.bss\n.balign 16\narena: .zero 256\n')
    for name,path in [('assets',out/'assets.S'),('action',out/'action.S'),('portal',ROOT/'userspace/runtime/abi/sysv/portal.S')]:
        command([llvm/'clang.exe',*flags,'-c',path,'-o',out/(name+'.o')],'compile-ui-'+name)
    # C++ uses the SysV SSE floating-point ABI. Resolve its libm symbols before
    # Rust's soft-float compiler-builtins archive, which also exports weak libm names.
    archives=[OUT/'engine/librmlui.a',OUT/'engine/freetype/libfreetype.a',OUT/'runtime/lib/libc++.a',OUT/'libc/libbmo-compute.a',out/'libraster.a']
    command([llvm/'ld.lld.exe','-static','--gc-sections','--why-extract='+str(out/'extract.tsv'),'-T',here/'guest.ld',
        *[out/(x+'.o') for x in ('portal','guest','assets','action','arena','services','new')],
        '--start-group',*archives,'--end-group','-o',out/'rmlui.elf'],'link-native-ui')
    check_math_providers((out/'extract.tsv').read_text())
    undefined=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--undefined-only',str(out/'rmlui.elf')],text=True)
    if undefined.strip():raise ValueError('Unresolved native UI: '+undefined)
    check_sections((out/'rmlui.elf').read_bytes())
    sys.path.insert(0,str(ROOT/'tools'))
    from host.importers.elf import pack_elf
    from host.sbef.format import inspect
    sbef=pack_elf((out/'rmlui.elf').read_bytes(),abi=1,profile='rmlui-native-v1')
    (out/'rmlui.sbef').write_bytes(sbef)
    report=inspect(sbef,profile='rmlui-native-v1')
    (out/'admission.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(out/'rmlui.elf')],text=True)
    symbols={s[0]:int(s[2],16) for line in symbols.splitlines() if len(s:=line.split())>=3}
    manifest=dict(state=symbols['bmo_ui_state'],pixels=symbols['bmo_ui_pixels'],desktop=args.desktop)
    if args.desktop:
        manifest.update(director=symbols['bmo_ui_director'],keyboard_focus=symbols['bmo_ui_keyboard_focus'])
    if args.msvc_panel_cc:
        manifest['msvc_panel_draws']=symbols['bmo_ui_msvc_draws']
    if args.usb:manifest.update(usb=args.usb,usb_reports=symbols['bmo_ui_usb_reports'])
    if args.amdvi_post:manifest['amdvi_post']=True
    if args.dma_census:manifest['dma_census']=True
    if args.storage_state:manifest['storage_state']=True
    if args.usb=='both':
        manifest.update(usb_keyboard_reports=symbols['bmo_ui_usb_keyboard_reports'],
            usb_mouse_reports=symbols['bmo_ui_usb_mouse_reports'],mouse_edges=symbols['bmo_ui_mouse_edges'],
            keyboard_leds=True)
    (out/'symbols.json').write_text(json.dumps(manifest,indent=2)+'\n')
    artifacts={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('rmlui.elf','rmlui.sbef','symbols.json')}
    (out/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n',encoding='ascii')
    print('Native ELF/SBEF: '+str(out))


if __name__=='__main__':main()
