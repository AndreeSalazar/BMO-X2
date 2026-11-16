"""Build only the explicit native UI gate/loader and execute the normal CASM ABI fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from build import ROOT,OUT,command

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('abi_run',type=Path)
    args=parser.parse_args()
    here=OUT/'guest'
    artifacts=json.loads((here/'artifacts.json').read_text())
    for name in ('rmlui.elf','rmlui.sbef','symbols.json'):
        if hashlib.sha256((here/name).read_bytes()).hexdigest()!=artifacts[name]:
            raise ValueError('Stale native artifact: '+name+'; run guest.py successfully before QEMU')
    llvm=Path(os.environ['ProgramFiles'])/'LLVM/bin'
    for name,source in [('gate','kernel/syscalls/session_gate.S'),('loader','kernel/loader/doom_engine_loader.S')]:
        command([llvm/'clang.exe','--target=x86_64-unknown-none-elf','-DDOOM_ENGINE','-DDESKTOP_DOOM','-DRMLUI_NATIVE','-c',ROOT/source,'-o',here/(name+'.o')],'assemble-ui-'+name)
        command([llvm/'llvm-objcopy.exe','-O','binary','--only-section=.text',here/(name+'.o'),here/(name+'.bin')],'extract-ui-'+name)
    command([sys.executable,ROOT/'tools/boot/doom_qemu.py',args.abi_run,here/'rmlui.sbef',
        '--session-gate',here/'gate.bin','--external-loader',here/'loader.bin','--rmlui-native',here/'symbols.json'],'qemu-native-ui')
    print((OUT/'qemu-native-ui.log').read_text(errors='replace'))

if __name__=='__main__':main()
