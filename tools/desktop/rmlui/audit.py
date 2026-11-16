"""Inventory the actual HOST engine's port blockers; never imply DLL -> SBEF conversion."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from host.importers.pe import probe_pe
from host.sbef.format import inspect
from host.diagnostics import Rejection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--llvm',type=Path,default=Path(os.environ['ProgramFiles'])/'LLVM/bin')
    args=parser.parse_args()
    native=ROOT/'build/rmlui-host/native/bmo_rmlui_host.dll'
    raw=native.read_bytes()
    output=subprocess.check_output([str(args.llvm/'llvm-readobj.exe'),'--coff-imports',str(native)],text=True)
    imports=[]
    for block in re.findall(r'Import \{(.*?)\n\}',output,re.S):
        imports.append(dict(library=re.search(r'Name: (\S+)',block)[1],
            symbols=re.findall(r'Symbol: (.*?) \(\d+\)',block)))
    if not imports:
        raise ValueError('No se extrajo inventario de importaciones; no declarar limpio')
    try:
        admission=probe_pe(raw)
    except Rejection as error:
        admission=dict(CanPack=False,Blockers=[error.report()])
    report=dict(evidence='HOST', engine_ring3_ready=False, dll_sha256=hashlib.sha256(raw).hexdigest(),
        native_bytes=len(raw), imports=imports, admission=admission,
        next_requirements=[
            'Build freestanding C++/FreeType with audited standard library dependencies',
            'Bound allocator, file/time/font services and native startup; remove Windows imports',
            'Rust event/lifetime bridge for DIRECTOR and ULTRA-J native actions',
            'Dirty surfaces, bounded resource ownership and presentation via existing capabilities',
            'Separate measured loader profile if engine exceeds current external 16 KiB budget',
            'QEMU input/render/lifecycle/permission tests before any METAL deployment'])
    adapter=ROOT/'build/rmlui-host/native/CMakeFiles/bmo_rmlui_host.dir/engine.cpp.obj'
    if adapter.exists():
        symbols=subprocess.check_output([str(args.llvm/'llvm-nm.exe'),'--undefined-only','--format=posix',str(adapter)],text=True)
        undefined=[line.split()[0] for line in symbols.splitlines() if line.strip()]
        windows={symbol for library in imports if library['library'].lower()=='kernel32.dll' for symbol in library['symbols']}
        direct=[symbol for symbol in undefined if symbol.removeprefix('__imp_') in windows]
        if direct:
            raise ValueError('Adaptador con dependencia directa de Windows: '+repr(direct))
        report['engine_adapter_object']=dict(SHA256=hashlib.sha256(adapter.read_bytes()).hexdigest(),
            UndefinedSymbols=undefined,DirectKernel32Imports=direct,Freestanding=False,
            Scope='Only engine.cpp object; RmlUi, FreeType, STL and compiler runtime still need adaptation')
    sbef=ROOT/'build/rmlui-guest/raster.sbef'
    if sbef.exists():
        report['shared_rust_probe']=inspect(sbef.read_bytes())
        report['shared_rust_probe']['SHA256']=hashlib.sha256(sbef.read_bytes()).hexdigest()
        report['shared_rust_probe']['AdditionalUserStackMappedBytes']=4096
        elf=sbef.with_suffix('.elf')
        undefined=subprocess.check_output([str(args.llvm/'llvm-nm.exe'),'--undefined-only',str(elf)],text=True)
        if undefined.strip():
            raise ValueError('El ELF Rust conserva simbolos sin resolver: '+undefined)
        report['shared_rust_probe']['UnresolvedSymbols']=[]
    target=ROOT/'build/rmlui-host/port-audit.json'
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(dict(Report=str(target),NativeBytes=len(raw),
        ImportedLibraries=len(imports),ImportedSymbols=sum(len(i['symbols']) for i in imports),
        EngineRing3Ready=False,PeCanPack=report['admission']['CanPack']),indent=2))


if __name__=='__main__':
    main()
