"""Recover a test NVMe namespace with fresh queues in the translated QEMU lab."""
import hashlib
import struct
import time

from host.gpu.qemu_dma import AMDVI, READ_WRITE, require

REQUESTER = 0x48
PAGE = 4096
SECTOR = 8
CONTENTS = hashlib.shake_256(b'BMO-X2 NVMe DMA sector').digest(512)
DISK = bytes(SECTOR * 512) + CONTENTS + bytes(1024*1024 - (SECTOR+1)*512)
WITNESS = bytes([0xa5]) * (5*PAGE)
ROOT_OFFSET = 0x12000
BACKING_OFFSET = 0x15000
IOVA_OFFSET = 0x1a000
QUEUE_DEPTH = 4


def read32(machine, bar, offset):
    return int(machine.command('readl',bar+offset),16)


def write32(machine, bar, offset, value):
    machine.command('writel',bar+offset,value)


def wait_for(observe, ready, description):
    deadline = time.monotonic()+5
    while True:
        value = observe()
        if ready(value):
            return value
        if time.monotonic()>=deadline:
            raise ValueError(f'NVMe {description}: {value!r}')
        time.sleep(.01)


def wait_status(machine, bar, mask, expected):
    def observe():
        value = read32(machine,bar,0x1c)
        require(value!=0xffffffff and not value&2, f'NVMe CSTS fallo: {value:#x}')
        return value
    return wait_for(observe,lambda value: value&mask==expected,
                    f'CSTS no alcanzo {expected:#x} con mascara {mask:#x}')


def shutdown(machine, command, bar):
    """Return with QEMU paused and the controller disabled."""
    config = read32(machine,bar,0x14)
    if not config&1:
        require(not read32(machine,bar,0x1c)&0x43, 'NVMe deshabilitado sigue activo')
        return None
    require(config&0xc000==0 and read32(machine,bar,0x1c)&0x4f==1,
            'NVMe no estaba listo para cierre normal')
    command('cont')
    try:
        write32(machine,bar,0x14,config|0x4000)
        acknowledgement = wait_status(machine,bar,0x4e,8)
        write32(machine,bar,0x14,config&~0xc001)
        wait_status(machine,bar,0x43,0)
        require(not read32(machine,bar,0x14)&0xc001, 'NVMe conserva EN o SHN')
        return acknowledgement
    finally:
        command('stop')


def check_domain(machine, scratch):
    root, backing, iova = (scratch+off for off in (ROOT_OFFSET,BACKING_OFFSET,IOVA_OFFSET))
    entry = struct.unpack('<4Q',machine.get_bytes(scratch+REQUESTER*32,32))
    require(entry==(root|READ_WRITE|0x403,4,0,0), 'NVMe no tiene dominio exclusivo 4')
    expected = {}
    for page in range(5):
        address = iova+page*PAGE
        index = address>>21
        leaf = root+PAGE*(1+index-(iova>>21))
        require(machine.read(root+index*8)==leaf|READ_WRITE|0x201, 'Entrada raiz NVMe inesperada')
        expected.setdefault(leaf,{})[(address>>12)&511]=(backing+page*PAGE)|READ_WRITE|1
    table = struct.unpack('<512Q',machine.get_bytes(root,PAGE))
    require(sum(bool(entry) for entry in table)==len(expected), 'NVMe raiz contiene otros rangos')
    for leaf, mappings in expected.items():
        entries = struct.unpack('<512Q',machine.get_bytes(leaf,PAGE))
        require(all(entry==mappings.get(index,0) for index,entry in enumerate(entries)),
                'NVMe dominio concede paginas fuera de sus cinco IOVA')


def read_sector(machine, command, bar, bar_size, scratch, input_activity):
    backing,iova = scratch+BACKING_OFFSET,scratch+IOVA_OFFSET
    check_domain(machine,scratch)
    require(machine.read(AMDVI+0x18)&0x1005==0x1005, 'AMD-Vi apagado durante NVMe')
    original = machine.pci(4,word=True,requester=REQUESTER)
    require(original&6==2 and not read32(machine,bar,0x14)&1 and not read32(machine,bar,0x1c)&0x43,
            'NVMe no esta quiescente con su BAR disponible')
    cap = machine.read(bar)
    stride = 4 << ((cap>>32)&15)
    require(cap&0xffff>=QUEUE_DEPTH-1 and cap>>37&1 and cap>>48&15==0
            and 0x1000+3*stride+4<=bar_size, 'NVMe CAP fuera del perfil QEMU')
    event_tail = machine.read(AMDVI+0x2018)
    machine.put_bytes(backing,bytes(5*PAGE))
    machine.put_bytes(iova,WITNESS)
    def submit(qid, slot, cid, opcode, nsid, prp1, cdw10, cdw11=0):
        sq, cq = backing+(2*qid)*PAGE, backing+(2*qid+1)*PAGE
        entry = bytearray(64)
        struct.pack_into('<II',entry,0,opcode | cid<<16,nsid)
        struct.pack_into('<Q',entry,24,prp1)
        struct.pack_into('<II',entry,40,cdw10,cdw11)
        machine.put_bytes(sq+slot*64,entry)
        write32(machine,bar,0x1000+2*qid*stride,slot+1)
        result = wait_for(lambda: struct.unpack('<HHHH',machine.get_bytes(cq+slot*16+8,8)),
                          lambda value: value[3]&1, f'CQ{qid} CID {cid} sin completar')
        require(result==(slot+1,qid,cid,1), f'NVMe CQ{qid} CID {cid} fallo: {result}')
        write32(machine,bar,0x1000+(2*qid+1)*stride,slot+1)

    machine.pci(4,original|4,word=True,requester=REQUESTER)
    try:
        write32(machine,bar,0x0c,0xffffffff)  # Poll CQ without legacy interrupts.
        write32(machine,bar,0x24,(QUEUE_DEPTH-1)*0x10001)
        machine.write(bar+0x28,iova)
        machine.write(bar+0x30,iova+PAGE)
        command('cont')
        try:
            write32(machine,bar,0x14,0x00460001)
            wait_status(machine,bar,0x43,1)
            queue = (QUEUE_DEPTH-1)<<16 | 1
            submit(0,0,1,0x05,0,iova+3*PAGE,queue,1)
            submit(0,1,2,0x01,0,iova+2*PAGE,queue,0x10001)
            submit(1,0,3,0x02,1,iova+4*PAGE,SECTOR)
            input_activity()
            payload = machine.get_bytes(backing+4*PAGE,512)
            require(payload==CONTENTS and machine.get_bytes(iova,len(WITNESS))==WITNESS,
                    'NVMe no escribio el sector en su respaldo traducido')
            require(machine.read(AMDVI+0x2018)==event_tail, 'AMD-Vi registro un fallo NVMe')
        finally:
            command('stop')
        require(shutdown(machine,command,bar) is not None, 'NVMe no confirmo cierre tras leer')
        return hashlib.sha256(payload).hexdigest()
    finally:
        # On failure the lab VM is discarded with its reservation intact.
        machine.pci(4,original,word=True,requester=REQUESTER)
        require(not machine.pci(4,word=True,requester=REQUESTER)&4, 'NVMe mantiene BME')


def verify_guest_read(machine, command, bar, scratch, context, guest_request, input_activity):
    """Give only the operation number to the guest. Observe the output."""
    backing,iova = scratch+BACKING_OFFSET,scratch+IOVA_OFFSET
    check_domain(machine,scratch)
    require(machine.read(AMDVI+0x18)&0x1005==0x1005, 'AMD-Vi apagado durante NVMe')
    original = machine.pci(4,word=True,requester=REQUESTER)
    require(original&6==2 and not read32(machine,bar,0x14)&1, 'NVMe no esta quiescente')
    before = machine.read(context+0xbc0)
    event_tail = machine.read(AMDVI+0x2018)
    machine.put_bytes(iova,WITNESS)
    guest_request(4)
    require(machine.read(context+0xbc0)==before+1 and machine.read(context+0xbd0)==7
            and machine.read(context+0xbc8)&0x4e==8, 'Falta lectura y cierre NVMe desde Ring 0')
    require(machine.get_bytes(context+0x15408,8)==bytes(8)
            and machine.get_bytes(scratch+0xd000,24)==bytes(24), 'NVMe dejo una ventana MMIO abierta')
    require(machine.pci(4,word=True,requester=REQUESTER)==original
            and not read32(machine,bar,0x14)&0xc001 and not read32(machine,bar,0x1c)&0x43,
            'NVMe mantiene BME o sigue activo')

    entries = [(0x1008,(1,0,1,1)), (0x1018,(2,0,2,1)), (0x3008,(1,1,3,1))]
    require(all(struct.unpack('<4H',machine.get_bytes(backing+offset,8))==expected
                for offset,expected in entries), 'Completados NVMe distintos de la secuencia esperada')
    payload = machine.get_bytes(backing+4*PAGE,512)
    require(payload==CONTENTS and machine.get_bytes(iova,len(WITNESS))==WITNESS,
            'NVMe no entrego el sector en su respaldo traducido')
    require(machine.read(AMDVI+0x2018)==event_tail, 'AMD-Vi registro un nuevo fallo NVMe')
    command('cont')
    try:
        input_activity()
    finally:
        command('stop')
    return hashlib.sha256(payload).hexdigest()
