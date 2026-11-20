"""Read one fixed SATA sector through the guest's AHCI domain in QEMU."""

import hashlib
import struct
import time

from host.gpu.qemu_dma import AMDVI, require


REQUESTER = 0x30
SECTOR = 8
CONTENTS = hashlib.shake_256(b'BMO-X2 AHCI DMA sector').digest(512)
DISK = bytes(SECTOR * 512) + CONTENTS + bytes(1024*1024 - (SECTOR+1)*512)
BUFFER_OFFSET = 0x10000
IOVA_OFFSET = 0x11000
WITNESS = bytes([0xa5])*512


def read_sector(machine, command, bar, scratch, input_activity):
    port = bar+0x100
    buffer, iova = scratch+BUFFER_OFFSET, scratch+IOVA_OFFSET
    require(machine.read(AMDVI+24) & 0x1005 == 0x1005, 'AMD-Vi inactivo para la lectura AHCI')
    original = machine.pci(4, word=True, requester=REQUESTER)
    require(not original & 4, 'AHCI conserva bus mastering antes de tomar el puerto')

    def read(address):
        return int(machine.command('readl', address), 16)

    def write(address, value):
        machine.command('writel', address, value)

    def stop():
        write(port+0x18, read(port+0x18) & ~1)
        require(not read(port+0x18) & 0x8000, 'El motor AHCI no detuvo los comandos')
        write(port+0x18, read(port+0x18) & ~0x10)
        require(not read(port+0x18) & 0x4000, 'El motor AHCI no detuvo la recepcion FIS')

    machine.pci(4, original | 2, word=True, requester=REQUESTER)
    try:
        require(read(bar+0xc) & 1 and read(port+0x28) & 15 == 3, 'Falta el disco SATA del laboratorio')
        require(not (read(port+0x34) or read(port+0x38)), 'AHCI tiene comandos pendientes')
        stop()
        write(bar+4,(read(bar+4) | 0x80000000) & ~2)
        write(port+0x14,0)
        write(port+0x10,0xffffffff)
        write(port+0x30,0xffffffff)
        tail = machine.read(AMDVI+0x2018)
        machine.put_bytes(buffer, bytes(4096))
        machine.put_bytes(buffer+0x800,WITNESS)
        machine.put_bytes(iova, bytes([0xa5])*4096)

        # One command header, one Register H2D FIS and one PRDT entry.
        # All guest-visible AHCI pointers are IOVAs inside the same page.
        machine.put_bytes(buffer,struct.pack('<IIII',5 | 1<<16,0,iova+0x500,0))
        fis = bytes((0x27,0x80,0x25,0,SECTOR,0,0,0x40,0,0,0,0,1,0,0,0,0,0,0,0))
        machine.put_bytes(buffer+0x500,fis)
        machine.put_bytes(buffer+0x580,struct.pack('<IIII',iova+0x800,0,0,511))
        for offset,value in ((0,iova),(4,0),(8,iova+0x400),(12,0)):
            write(port+offset,value)
        machine.pci(4, original | 6, word=True, requester=REQUESTER)
        write(port+0x18,read(port+0x18) | 0x10)
        require(not read(port+0x20) & 0x88, f'AHCI no esta listo: TFD={read(port+0x20):#x}')
        write(port+0x18,read(port+0x18) | 1)
        write(port+0x38,1)
        command('cont')
        try:
            input_activity()
            deadline = time.monotonic()+10
            while read(port+0x38) & 1:
                require(time.monotonic()<deadline, 'AHCI no completo READ DMA EXT')
                time.sleep(.01)
        finally:
            command('stop')
        status = read(port+0x10)
        require(not status & 0x7d800000 and not read(port+0x20) & 1,
                f'La lectura AHCI fallo: IS={status:#x}, TFD={read(port+0x20):#x}')
        prdbc, = struct.unpack('<I',machine.get_bytes(buffer+4,4))
        payload = machine.get_bytes(buffer+0x800,512)
        require(prdbc==512 and payload==CONTENTS and machine.get_bytes(iova,4096)==bytes([0xa5])*4096,
                'El sector AHCI no llego a la pagina fisica traducida')
        require(machine.read(AMDVI+0x2018)==tail, 'AMD-Vi registro un fallo durante la lectura AHCI')
        return hashlib.sha256(payload).hexdigest()
    finally:
        try:
            stop()
            for offset in (0,4,8,12):
                write(port+offset,0)
        finally:
            machine.pci(4, original, word=True, requester=REQUESTER)
        require(not machine.pci(4,word=True,requester=REQUESTER) & 4, 'AHCI sigue con bus mastering')
