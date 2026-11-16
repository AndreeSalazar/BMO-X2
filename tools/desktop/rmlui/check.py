"""Native rejection/reinitialization checks; requires a built HOST DLL."""
import ctypes
import json
import tempfile
from pathlib import Path
from preview import package, main


def check():
    assets, _, _ = package()
    library = ctypes.CDLL(str(assets / 'bmo_rmlui_host.dll'))
    callback = ctypes.CFUNCTYPE(ctypes.c_int)
    native = library.bmo_rmlui_preview
    native.argtypes = [ctypes.c_char_p, ctypes.c_char_p, callback]
    native.restype = ctypes.c_int
    reject = callback(lambda: 0)
    with tempfile.TemporaryDirectory(prefix='bmo-rmlui-') as folder:
        output = Path(folder)
        status = native(str(assets).encode(), str(output).encode(), reject)
        report = json.loads((output / 'native.json').read_text())
        assert status == 3 and report['click_events'] == 1 and not report['callback_passed']
        assert report['adapter_geometry_bytes_after_shutdown'] == 0
        assert report['adapter_texture_bytes_after_shutdown'] == 0
        # Failed font input must tear down the engine, allowing another initialization.
        status = native(str(output).encode(), str(output).encode(), reject)
        assert status == 4 and (output / 'error.txt').read_text() == 'font load'
    main()
    print('PASS: rejected action, missing input, then successful reinitialization and ULTRA-J action')


if __name__ == '__main__':
    check()
