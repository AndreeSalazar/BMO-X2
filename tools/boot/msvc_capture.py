"""Observe the external MSVC fixture and its clock from QEMU."""
import json
from pathlib import Path
import struct
import time

from cpu_config import register
from desktop_session_capture import verify_external_rejection


def verify_sections(command, memory, prefix, image, case, symbols_path):
    if case == 'external-permissions':
        result = verify_external_rejection(command, memory, image)
        if memory(0x4000000, 4096, 'msvc-rejected-text') != bytes(4096):
            raise ValueError('MSVC text copied before admission')
        return result
    symbols = json.loads(symbols_path.read_text(encoding='ascii'))
    if any(not 0x40400000 <= symbols[name] <= 0x40402000 - size
           for name, size in [('phase', 8), ('first_ms', 8), ('second_ms', 8), ('scratch', 6000), ('written', 4)]):
        raise ValueError('MSVC fixture symbols outside RW budget')

    def word(name):
        return struct.unpack('<Q', memory(symbols[name] - 0x3c000000, 8, name))[0]

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if word('phase') == 0x53454332:
            regs = command('human-monitor-command', {'command-line': 'info registers'})
            if 'CPL=3' not in regs or not 0x40000000 <= register(regs, 'RIP') < 0x40200000:
                raise ValueError('MSVC fixture outside CPL3')
            first, second = word('first_ms'), word('second_ms')
            scratch = memory(symbols['scratch'] - 0x3c000000, 6000, 'scratch')
            if second < first + 20 or scratch != b'\0M' + bytes(5998):
                raise ValueError('MSVC clock or data verification failed')
            hello = b'Hola mundo desde C++ / MSVC en BMO-X2\r\n'
            serial = Path(str(prefix)+'-serial.log').read_bytes()
            written = struct.unpack('<I', memory(symbols['written'] - 0x3c000000, 4, 'written'))[0]
            if serial.count(hello) != 1 or written != len(hello):
                raise ValueError('MSVC stdout mismatch')
            return dict(Case='normal', Passed=True, Evidence='QEMU', CPL=3,
                        InitializedDataVerified=True, ZeroFillVerified=True,
                        RustClockVerified=True, FirstMs=first, SecondMs=second,
                        SerialHelloVerified=True, WrittenBytes=written)
        time.sleep(.03)
    raise ValueError('MSVC clock fixture never completed')
