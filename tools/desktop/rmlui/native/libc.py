"""Build selected, unchanged musl computation routines, without Linux services."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from build import ROOT, OUT, DEPS, generate_headers, command, write_if_changed
from fetch import check_sources


def main():
    check_sources()
    musl = DEPS / 'musl-1.2.5'
    output = OUT / 'libc'
    output.mkdir(parents=True, exist_ok=True)
    includes = generate_headers()
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    flags = ['--target=x86_64-unknown-none-elf', '-Os', '-ffreestanding', '-fno-builtin',
             '-fno-stack-protector', '-fno-pic', '-fno-pie', '-mno-red-zone',
             '-ffunction-sections', '-fdata-sections', '-fno-unwind-tables',
             '-fno-asynchronous-unwind-tables', '-D_GNU_SOURCE']
    flags += ['-I'+str(p) for p in [musl/'src/include', musl/'src/internal', *includes]]
    sources = list((musl/'src/math').glob('*.c'))
    names = {
        'string': 'memcpy memset memmove memcmp memchr memrchr strlen strnlen strcmp strncmp strcpy strncpy strcat strchr strchrnul strrchr strstr stpcpy stpncpy strcspn strspn',
        'stdlib': 'abs atoi atof strtod strtol qsort qsort_nr',
        'ctype': 'isdigit tolower isspace',
        'stdio': 'snprintf vsnprintf vfprintf sscanf vsscanf vfscanf __towrite __toread __uflow __overflow fwrite',
        'internal': 'shgetc floatscan intscan',
        'multibyte': 'mbsinit wctomb',
    }
    sources += [musl/'src'/folder/(name+'.c') for folder, names in names.items() for name in names.split()]
    sources += [musl/'src/setjmp/x86_64/setjmp.s', musl/'src/setjmp/x86_64/longjmp.s']
    utf8 = output/'utf8'
    utf8.mkdir(exist_ok=True)
    header = (musl/'src/multibyte/internal.h').read_text().replace(
        '#include "locale_impl.h"', '#include <stdlib.h>\n#undef MB_CUR_MAX\n#define MB_CUR_MAX 4')
    write_if_changed(utf8/'internal.h', header)
    for name in ('internal', 'wcrtomb', 'mbrtowc'):
        target = utf8/(name+'.c')
        write_if_changed(target, (musl/('src/multibyte/'+name+'.c')).read_text())
        sources.append(target)
    common=Path(__file__).read_bytes()+(utf8/'internal.h').read_bytes()+(OUT/'headers/bits/alltypes.h').read_bytes()
    common+=subprocess.check_output([str(llvm/'clang.exe'),'--version'])
    def compile(source):
        relative = source.relative_to(utf8) if source.is_relative_to(utf8) else source.relative_to(musl/'src')
        object = output / ('_'.join(relative.parts)+'.o')
        args = [str(llvm/'clang.exe'), *flags, '-c', str(source), '-o', str(object)]
        stamp = object.with_suffix('.json')
        key = hashlib.sha256(source.read_bytes()+json.dumps(args).encode()+common).hexdigest()
        if not object.is_file() or not stamp.is_file() or stamp.read_text()!=key:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(str(source)+'\n'+result.stdout+result.stderr)
            stamp.write_text(key)
        return object
    with ThreadPoolExecutor(max_workers=4) as pool:
        objects = list(pool.map(compile, sources))
    archive=output/'libbmo-compute-next.a'
    archive.unlink(missing_ok=True)
    command([llvm/'llvm-ar.exe', 'rcs', archive, *objects], 'archive-compute')
    archive.replace(output/'libbmo-compute.a')
    print(f'PASS: {len(objects)} native computation units; no libc OS sources')


if __name__=='__main__':
    main()
