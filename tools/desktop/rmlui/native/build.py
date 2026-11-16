"""Build actual x86-64 ELF runtime/RmlUi objects; never substitute a Windows library."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from fetch import check_sources

ROOT=Path(__file__).resolve().parents[4]
DEPS=ROOT/'build/deps'
OUT=ROOT/'build/rmlui-native'


def write_if_changed(path,text):
    if not path.is_file() or path.read_text()!=text:
        path.write_text(text,encoding='ascii',newline='\n')


def generate_headers():
    musl=DEPS/'musl-1.2.5'
    target=OUT/'headers/bits'
    target.mkdir(parents=True,exist_ok=True)
    source=(musl/'arch/x86_64/bits/alltypes.h.in').read_text()+'\n'+(musl/'include/alltypes.h.in').read_text()
    # Same conditional typedef expansion as upstream tools/mkalltypes.sed.
    for kind in ('TYPEDEF','STRUCT','UNION'):
        if kind=='TYPEDEF':
            source=re.sub(r'^TYPEDEF (.*) ([^ ]+);$',lambda m:
                f'#if defined(__NEED_{m[2]}) && !defined(__DEFINED_{m[2]})\ntypedef {m[1]} {m[2]};\n#define __DEFINED_{m[2]}\n#endif\n',source,flags=re.M)
        else:
            prefix=kind.lower()
            source=re.sub(r'^'+kind+r' * ([^ ]+) (.*);$',lambda m:
                f'#if defined(__NEED_{prefix}_{m[1]}) && !defined(__DEFINED_{prefix}_{m[1]})\n{prefix} {m[1]} {m[2]};\n#define __DEFINED_{prefix}_{m[1]}\n#endif\n',source,flags=re.M)
    write_if_changed(target/'alltypes.h',source)
    # Types/C declarations are reused, not the Linux syscall namespace.
    # Publishing SYS_futex would falsely advertise a kernel service on this target.
    write_if_changed(target/'syscall.h','/* BMO-X2 has no Linux syscall numbers. */\n')
    return [OUT/'headers',musl/'arch/x86_64',musl/'arch/generic',musl/'include']


def command(args,name,*,cwd=None):
    log=OUT/(name+'.log')
    with log.open('w') as output:
        result=subprocess.run(list(map(str,args)),stdout=output,stderr=subprocess.STDOUT,
                              cwd=cwd,
                              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if result.returncode:
        print('\n'.join(log.read_text(errors='replace').splitlines()[-45:]))
        raise SystemExit(f'Native step failed: {name}; full log: {log}')
    print(f'OK: {name}',flush=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    check_sources()
    includes=generate_headers()
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    vs=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    version=(vs/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt').read_text().strip()
    nmake=vs/'VC/Tools/MSVC'/version/'bin/Hostx64/x64/nmake.exe'
    flags='-D_POSIX_C_SOURCE=200809L -D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE '+' '.join('-I"'+p.as_posix()+'"' for p in includes)
    runtime=DEPS/'llvm-19.1.7'
    command(['cmake','-G','NMake Makefiles','-S',runtime/'runtimes','-B',OUT/'runtime',
        '-DCMAKE_MAKE_PROGRAM='+str(nmake),'-DCMAKE_TOOLCHAIN_FILE='+str(Path(__file__).with_name('toolchain.cmake')),
        '-DPython3_EXECUTABLE='+sys.executable,
        '-DCMAKE_BUILD_TYPE=MinSizeRel','-DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi',
        '-DLLVM_INCLUDE_TESTS=OFF','-DLIBCXX_INCLUDE_TESTS=OFF','-DLIBCXXABI_INCLUDE_TESTS=OFF','-DLIBCXX_INCLUDE_BENCHMARKS=OFF',
        '-DLIBCXX_HAS_PTHREAD_LIB=OFF','-DLIBCXX_HAS_RT_LIB=OFF','-DLIBCXX_HAS_ATOMIC_LIB=OFF',
        '-DLIBCXXABI_HAS_GCC_S_LIB=OFF','-DLIBCXXABI_HAS_GCC_LIB=OFF','-DLIBCXXABI_HAS_PTHREAD_LIB=OFF',
        '-DLIBCXXABI_HAS_CXA_THREAD_ATEXIT_IMPL=OFF',
        '-DLIBCXX_ENABLE_SHARED=OFF','-DLIBCXXABI_ENABLE_SHARED=OFF',
        '-DLIBCXX_ENABLE_THREADS=OFF','-DLIBCXXABI_ENABLE_THREADS=OFF',
        '-DLIBCXX_ENABLE_EXCEPTIONS=OFF','-DLIBCXXABI_ENABLE_EXCEPTIONS=OFF',
        '-DLIBCXX_ENABLE_RTTI=OFF',
        '-DLIBCXX_ENABLE_FILESYSTEM=OFF','-DLIBCXX_ENABLE_LOCALIZATION=OFF',
        '-DLIBCXX_ENABLE_RANDOM_DEVICE=OFF','-DLIBCXX_ENABLE_WIDE_CHARACTERS=OFF',
        '-DLIBCXX_ENABLE_TIME_ZONE_DATABASE=OFF','-DLIBCXX_ENABLE_MONOTONIC_CLOCK=ON',
        '-DLIBCXXABI_USE_LLVM_UNWINDER=OFF','-DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON',
        '-DCMAKE_C_FLAGS='+flags+' -ffreestanding -fno-stack-protector -fno-pic -fno-pie -mno-red-zone -ffunction-sections -fdata-sections',
        '-DCMAKE_CXX_FLAGS='+flags+' -ffreestanding -nostdinc++ -fno-stack-protector -fno-pic -fno-pie -mno-red-zone -ffunction-sections -fdata-sections -fno-threadsafe-statics -fno-use-cxa-atexit'], 'configure-runtime')
    command(['cmake','--build',OUT/'runtime','--target','cxx','cxxabi'],'build-runtime')
    cppflags='-I"'+(OUT/'runtime/include/c++/v1').as_posix()+'" '+flags+' -ffreestanding -nostdinc++ -fno-exceptions -fno-rtti -fno-stack-protector -fno-pic -fno-pie -mno-red-zone -ffunction-sections -fdata-sections -fno-threadsafe-statics -fno-use-cxa-atexit'
    command(['cmake','-G','NMake Makefiles','-S',Path(__file__).parent,'-B',OUT/'engine',
        '-DCMAKE_MAKE_PROGRAM='+str(nmake),'-DCMAKE_TOOLCHAIN_FILE='+str(Path(__file__).with_name('toolchain.cmake')),
        '-DCMAKE_BUILD_TYPE=MinSizeRel','-DCMAKE_C_FLAGS='+flags+' -ffreestanding -fno-stack-protector -fno-pic -fno-pie -mno-red-zone -ffunction-sections -fdata-sections',
        '-DCMAKE_CXX_FLAGS='+cppflags], 'configure-engine')
    command(['cmake','--build',OUT/'engine','--target','rmlui_core'],'build-engine')
    command([sys.executable,Path(__file__).with_name('audit.py')],'audit-native')


if __name__=='__main__':
    main()
