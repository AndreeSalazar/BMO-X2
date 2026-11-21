"""Prueba DMA real del modelo AMD-Vi en QEMU, controlado por qtest."""

import argparse
import json
from pathlib import Path
import queue
import struct
import subprocess
import threading


AMDVI = 0xfed80000
EDU_BAR = 0xe1000000
EDU_REQUESTER = 4 << 3
DEVICE_TABLE = 0x200000
PAGE_TABLE = 0x201000
COMMAND_RING = 0x202000
EVENT_LOG = 0x203000
COMPLETION = 0x204000
BUFFER = 0x300000
IOVA = 0x100000
OUTSIDE = IOVA + 4096
DOMAIN = 1
READ_WRITE = (1 << 61) | (1 << 62)


class QTest:
    def __init__(self, process):
        self.process = process
        self.responses = queue.Queue()
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        for line in self.process.stdout:
            self.responses.put(line.strip())
        self.responses.put(None)

    def command(self, name, *args):
        line = ' '.join((name, *(hex(arg) if isinstance(arg, int) else arg for arg in args)))
        result = self.exchange(line)
        if result != 'OK' and not result.startswith('OK '):
            raise RuntimeError(f'{line}: {result}')
        return result[3:]

    def exchange(self, line):
        self.process.stdin.write(line + '\n')
        self.process.stdin.flush()
        try:
            result = self.responses.get(timeout=5)
        except queue.Empty:
            raise RuntimeError(f'QEMU sin respuesta: {line}') from None
        if result is None:
            raise RuntimeError(f'QEMU cerro: {self.process.stderr.read().strip()}')
        return result

    def write(self, address, value):
        self.command('writeq', address, value)

    def read(self, address):
        return int(self.command('readq', address), 16)

    def put_bytes(self, address, content):
        self.command('write', address, len(content), '0x' + content.hex())

    def get_bytes(self, address, size):
        return bytes.fromhex(self.command('read', address, size).removeprefix('0x'))

    def pci(self, register, value=None, *, word=False, requester=EDU_REQUESTER):
        self.command('outl', 0xcf8, 0x80000000 | requester << 8 | register)
        if value is None:
            return int(self.command('inw' if word else 'inl', 0xcfc), 16)
        self.command('outw' if word else 'outl', 0xcfc, value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def submit_transfer(machine, source, target, size, command, *, bar=EDU_BAR):
    machine.write(bar + 0x80, source)
    machine.write(bar + 0x88, target)
    machine.write(bar + 0x90, size)
    machine.write(bar + 0x98, command)


def transfer(machine, source, target, size, command):
    submit_transfer(machine, source, target, size, command)
    machine.command('clock_step', 101_000_000)
    require(not machine.read(EDU_BAR + 0x98) & 1, 'EDU no completo la solicitud')


def faults(machine, offset, iova, size, *, event_log=EVENT_LOG, requester=EDU_REQUESTER, access=2):
    tail = machine.read(AMDVI + 0x2018)
    require(offset < tail < 4096 and tail % 16 == 0, f'Cola AMD-Vi invalida: {tail:#x}')
    log = machine.get_bytes(event_log + offset, tail - offset)
    addresses = []
    for event, address in struct.iter_unpack('<QQ', log):
        # QEMU records its requested permission bits, 1 for read and 2 for write.
        require((event >> 60, event & 0xffff) == (2, requester) and (event >> 48) & 3 == access,
                f'Evento AMD-Vi inesperado: {event:#x}')
        # Some QEMU builds leave the event address at zero. Report it verbatim.
        require(address == 0 or iova <= address < iova + size, f'Direccion de evento inesperada: {address:#x}')
        addresses.append(hex(address))
    return tail, addresses


def publish_command(machine, offset, low, high, completion_value, *,
                    command_ring=COMMAND_RING, completion=COMPLETION):
    machine.put_bytes(command_ring + offset, struct.pack('<QQQQ', low, high,
                                                         1 << 60 | completion | 1, completion_value))
    tail = offset + 32
    machine.write(AMDVI + 0x2008, tail)
    require(machine.read(AMDVI + 0x2000) == tail and machine.read(completion) == completion_value,
            'Comando AMD-Vi sin confirmar')


def verify(machine):
    require(machine.pci(0) == 0x11e81234, 'Falta el EDU virtual en 00:04.0')
    machine.pci(0x10, EDU_BAR)
    machine.pci(4, 2, word=True)
    require(int(machine.command('readl', EDU_BAR), 16) & 0xffffff == 0x0000ed,
            'BAR de EDU no responde')

    # One 4 KiB page at an IOVA different from its backing guest RAM.
    leaf = PAGE_TABLE + (IOVA >> 12) * 8
    entry = DEVICE_TABLE + EDU_REQUESTER * 32
    machine.put_bytes(entry, struct.pack('<QQQQ', PAGE_TABLE | READ_WRITE | (1 << 9) | 3, DOMAIN, 0, 0))
    machine.write(leaf, BUFFER | READ_WRITE | 1)
    machine.write(AMDVI, DEVICE_TABLE)
    machine.write(AMDVI + 0x08, COMMAND_RING | 8 << 56)
    machine.write(AMDVI + 0x10, EVENT_LOG | 8 << 56)
    machine.write(AMDVI + 0x18, (1 << 12) | (1 << 2) | 1)
    require(machine.read(AMDVI + 0x18) & 1, 'AMD-Vi no habilito traduccion')
    publish_command(machine, 0, 2 << 60 | EDU_REQUESTER, 0, 1)
    machine.pci(4, 6, word=True)

    payload = b'BMO-X2 AMD-Vi!'
    sentinel = bytes([0xa5]) * len(payload)
    machine.put_bytes(BUFFER, payload)
    machine.put_bytes(IOVA, sentinel)
    machine.put_bytes(IOVA + 0x100, sentinel)
    machine.put_bytes(OUTSIDE, sentinel)
    transfer(machine, IOVA, 0x40000, len(payload), 1)
    transfer(machine, 0x40000, IOVA + 0x100, len(payload), 3)
    copied = machine.get_bytes(BUFFER + 0x100, len(payload))
    require(copied == payload, f'DMA traducido no coincide: {copied.hex()} '
            f'(cola de eventos {machine.read(AMDVI + 0x2018):#x})')
    require(machine.get_bytes(IOVA + 0x100, len(payload)) == sentinel, 'DMA autorizado escribio en la IOVA fisica')
    require(machine.read(AMDVI + 0x2018) == 0, 'DMA autorizado genero un fallo')

    transfer(machine, 0x40000, OUTSIDE, len(payload), 3)
    fault_tail, outside_events = faults(machine, 0, OUTSIDE, len(payload))
    require(machine.get_bytes(OUTSIDE, len(payload)) == sentinel, 'DMA fuera del rango altero RAM')

    # Evict the populated translation, then wait for completion before retrying.
    machine.write(leaf, 0)
    publish_command(machine, 32, 3 << 60 | DOMAIN << 32, IOVA, 2)
    machine.put_bytes(BUFFER, sentinel)
    transfer(machine, 0x40000, IOVA, len(payload), 3)
    _, revoked_events = faults(machine, fault_tail, IOVA, len(payload))
    require(machine.get_bytes(BUFFER, len(payload)) == sentinel and
            machine.get_bytes(IOVA, len(payload)) == sentinel, 'DMA revocado altero RAM')
    machine.pci(4, 2, word=True)
    require(not machine.pci(4, word=True) & 4, 'EDU conserva bus mastering')
    return dict(translated_dma_bytes=len(payload), outside_range_iova=hex(OUTSIDE),
                outside_range_event_addresses=outside_events, revoked_iova=hex(IOVA),
                revoked_event_addresses=revoked_events,
                invalidation_completed=True, bus_master_disabled=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    args = parser.parse_args()
    launch = [str(args.qemu), '-machine', 'q35', '-accel', 'qtest', '-nodefaults', '-display', 'none',
              '-monitor', 'none', '-serial', 'none', '-m', '256', '-device', 'amd-iommu,dma-remap=on',
              '-device', 'edu,addr=04.0', '-qtest', 'stdio', '-qtest-log', 'none']
    with subprocess.Popen(launch, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding='ascii') as process:
        try:
            result = verify(QTest(process))
        finally:
            process.terminate()
            process.wait(timeout=5)
    version = subprocess.check_output([args.qemu, '--version'], text=True).splitlines()[0]
    print(json.dumps(dict(schema=1, evidence='QEMU qtest: emulated AMD-Vi with EDU', qemu=version,
                          guest_kernel_executed=False, physical_dma_verified=False, **result), indent=2))


if __name__ == '__main__':
    main()
