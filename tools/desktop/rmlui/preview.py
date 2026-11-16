"""Package and execute the real RmlUi HOST renderer with the ULTRA-J HOST VM."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Ultra-J'))
from compiler import compile_source
from runtime import run


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package():
    output = ROOT / 'build/rmlui-host/package'
    output.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'Ultra-J/examples/rmlui-desktop'
    rml = ROOT / 'build/deps/RmlUi-6.3'
    ft = ROOT / 'build/deps/freetype-2.14.3'
    files = {
        'main.rml': assets / 'main.rml', 'style.rcss': assets / 'style.rcss',
        'main.uj': assets / 'main.uj',
        'bmo_rmlui_host.dll': ROOT / 'build/rmlui-host/native/bmo_rmlui_host.dll',
        'LatoLatin-Regular.ttf': rml / 'Samples/assets/LatoLatin-Regular.ttf',
        'LatoLatin-Bold.ttf': rml / 'Samples/assets/LatoLatin-Bold.ttf',
        'RmlUi-LICENSE.txt': rml / 'LICENSE.txt',
        'Lato-LICENSE.txt': rml / 'Samples/assets/LICENSE.txt',
        'FreeType-LICENSE.txt': ft / 'LICENSE.TXT',
        'FreeType-FTL.txt': ft / 'docs/FTL.TXT',
        'dependencies.lock.json': Path(__file__).with_name('dependencies.lock.json'),
        'HOST-README.md': Path(__file__).with_name('README.md'),
    }
    for name, source in files.items():
        if not source.is_file():
            raise ValueError(f'Falta entrada HOST: {source}')
        destination = output / name
        if not destination.is_file() or sha(source) != sha(destination):
            shutil.copyfile(source, destination)
    program = compile_source((output / 'main.uj').read_bytes())
    (output / 'action.ujb').write_bytes(program)
    manifest = dict(schema=1, profile='rmlui-host-windows-x64', sbef=False, ring3_ready=False,
                    note='Native Windows proof plus Python HOST VM; no guest executable.',
                    files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p))
                           for p in sorted(output.iterdir()) if p.name in {*files, 'action.ujb'}})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
    return output, program, manifest


def memory():
    # Whole Python+native HOST process. This is not the guest kernel footprint.
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    *[(name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                       'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                       'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    counter = Counters(); counter.cb = ctypes.sizeof(counter)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counter), counter.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(working_set_bytes=counter.WorkingSetSize, peak_working_set_bytes=counter.PeakWorkingSetSize,
                private_bytes=counter.PrivateUsage, scope='Whole Python + RmlUi + FreeType + CPU adapter HOST process')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    output, program, manifest = package()
    baseline = memory()
    library = ctypes.CDLL(str(output / 'bmo_rmlui_host.dll'))
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int)
    actions, failures = [], []

    @callback_type
    def action():
        try:
            result = run(program)
            if len(result['Calls']) != 2 or result['LiveObjectBytes'] != 0:
                raise ValueError('La accion no cerro sus objetos o no ejecuto ambos metodos')
            actions.append(result)
            return 1
        except Exception as error:
            failures.append(str(error))
            return 0

    preview = library.bmo_rmlui_preview
    preview.argtypes = [ctypes.c_char_p, ctypes.c_char_p, callback_type]
    preview.restype = ctypes.c_int
    started = time.perf_counter()
    status = preview(str(output).encode('utf-8'), str(output.parent).encode('utf-8'), action)
    elapsed = (time.perf_counter() - started) * 1000
    if status or failures or len(actions) != 1:
        raise ValueError(f'RmlUi HOST fallo: status={status}, callbacks={len(actions)}, errors={failures}')
    native = json.loads((output.parent / 'native.json').read_text())
    report = dict(evidence='HOST', native=native, ultra_j=actions, baseline_memory=baseline,
                  final_memory=memory(), total_native_call_ms=elapsed,
                  packaged_files_bytes=sum(item['bytes'] for item in manifest['files'].values()),
                  dependency_policy='Windows CRT/SDK remain runtime dependencies, not included in package bytes',
                  sbef=False, ring3_ready=False, scripted_click=True)
    from PIL import Image
    for name in ('before', 'after'):
        image = Image.open(output.parent / f'{name}.bmp')
        image.convert('RGB').save(output.parent / f'{name}.png')
    if sha(output.parent / 'before.png') == sha(output.parent / 'after.png'):
        raise ValueError('La accion no cambio la imagen')
    (output.parent / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))
    print(output.parent / 'after.png')


if __name__ == '__main__':
    main()
