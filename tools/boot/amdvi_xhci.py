"""QEMU-only coexistence check for the native desktop's USB and virtual EDU."""

import struct
import sys
import time

from host.gpu.qemu_dma import (
    AMDVI, EDU_REQUESTER, QTest, READ_WRITE, faults,
    publish_command, require, submit_transfer,
)


PAGE = 4096
EDU_BUFFER = 0x40000


class SocketQTest(QTest):
    def __init__(self, socket):
        self.channel = socket.makefile('rwb')

    def exchange(self, line):
        self.channel.write((line + '\n').encode('ascii'))
        self.channel.flush()
        response = self.channel.readline().decode('ascii').strip()
        if not response:
            raise RuntimeError('QEMU cerró el canal qtest')
        return response


def dma_ranges(memory, context, scratch_pages):
    scratch, = struct.unpack('<Q', memory(context+0xb50, 8, 'amdvi-coexist-scratch'))
    usb, pages = struct.unpack('<QQ', memory(context+0xb8, 16, 'amdvi-coexist-usb'))
    for base, count in ((scratch, scratch_pages), (usb, pages)):
        require(base >= 0x100000 and base % PAGE == 0 and base + count*PAGE <= 0x10000000,
                'Reserva DMA fuera de la memoria del ensayo')
    require(pages == 14 and (scratch+scratch_pages*PAGE <= usb or usb+pages*PAGE <= scratch),
            'Reservas DMA contiguas solapadas')
    length, = struct.unpack('<Q', memory(context+0x50, 8, 'amdvi-coexist-map-length'))
    stride, = struct.unpack('<Q', memory(context+0x60, 8, 'amdvi-coexist-map-stride'))
    require(40 <= stride <= 256 and 0 < length <= 65536 and length % stride == 0, 'Mapa UEFI inválido')
    descriptors = memory(context+0x1000, length, 'amdvi-coexist-map')
    allocations = []
    for offset in range(0, length, stride):
        kind, base, _, count = struct.unpack_from('<I4xQQQ', descriptors, offset)
        if kind == 2:
            allocations.append((base, base + count*PAGE))
    require(all(any(start <= base and base+count*PAGE <= end for start,end in allocations)
                for base,count in ((scratch,scratch_pages),(usb,pages))), 'Reserva DMA sin propiedad EfiLoaderData')
    return scratch, usb, pages


def map_pages(machine, root, leaves, mappings):
    tables = {}
    for iova, backing in mappings:
        index = iova >> 21
        if index not in tables:
            tables[index] = next(leaves)
            machine.write(root + index*8, tables[index] | READ_WRITE | 0x201)
        leaf = tables[index] + ((iova >> 12) & 511)*8
        machine.write(leaf, backing | READ_WRITE | 1)
    return leaf


def run_transfer(machine, command, bar, source, destination, size, direction, activity=None):
    submit_transfer(machine, source, destination, size, direction, bar=bar)
    require(machine.read(bar + 0x98) & 1, 'EDU no inició la transferencia')
    command('cont')
    try:
        if activity:
            activity()
        deadline = time.monotonic() + 8
        while machine.read(bar + 0x98) & 1:
            require(time.monotonic() < deadline, 'EDU no completó la transferencia')
            time.sleep(.01)
    finally:
        command('stop')


def verify_coexistence(machine, command, memory, context, symbols, *, guest_dma=False):
    """Run at the first frozen desktop frame. Return with the guest paused."""
    scratch_pages = 14 if guest_dma else 13
    scratch, usb, pages = dma_ranges(memory, context, scratch_pages)
    devices = command('query-pci')
    require(len(devices) == 1 and not any('pci_bridge' in entry for entry in devices[0]['devices']),
            'Topología QEMU fuera del ensayo')
    functions = {entry['slot']*8 + entry['function']: entry for entry in devices[0]['devices']}
    xhci, = (rid for rid, entry in functions.items() if entry['qdev_id'] == 'bmo-native-xhci')
    require(machine.pci(0) == 0x11e81234 and machine.pci(4, word=True, requester=xhci) & 4,
            'Falta EDU o xHCI no está activo')
    disabled = {}
    edu_command = machine.pci(4, word=True)
    bar_register = machine.pci(0x10)
    bar, = (region['address'] for region in functions[EDU_REQUESTER]['regions'] if region['bar']==0)
    require(bar_register == bar and 0x80000000 <= bar < 0x100000000 and bar % 0x100000 == 0,
            'BAR0 de EDU difiere del recurso asignado por OVMF')
    require(not any(machine.read(AMDVI + off) for off in (0,8,16,24,0x2020)), 'AMD-Vi ya estaba activo')
    edu_idle_command = edu_command & ~4
    table, edu_root, usb_root = scratch, scratch+2*PAGE, scratch+4*PAGE
    commands, events, completion = (scratch+offset*PAGE for offset in (7,8,9))
    payload, iova, outside = (scratch+offset*PAGE for offset in (10,11,12))
    sentinel, data = bytes([0xa5])*8, b'BMOX2DMA'
    readers = [symbols[name]-0x3c000000 for name in ('usb_keyboard_reports','usb_mouse_reports')]

    def guest_request(operation, result=0):
        require(machine.read(context+0xb58)==0, 'El buzón del invitado está ocupado')
        machine.write(context+0xb58,operation)
        command('cont')
        try:
            deadline=time.monotonic()+10
            while machine.read(context+0xb58):
                require(time.monotonic()<deadline,'Ring 0 no consumió la orden DMA')
                time.sleep(.02)
        finally:
            command('stop')
        observed=machine.read(context+0xb60)
        require(observed==result, f'Orden DMA {operation}: estado {observed}, esperado {result}; '
                f'control={machine.read(AMDVI+24):#x}, lectura de cierre={machine.read(context+0xb70):#x}')
        require(machine.read(context+0x15408)==0, 'Ring 0 dejó una PDE de AMD-Vi activa')
        if result==0:
            require(machine.read(scratch+13*PAGE)==0 and machine.read(scratch+13*PAGE+16)==0,
                    'Ring 0 dejó dos páginas MMIO mapeadas')

    def counters():
        return [struct.unpack('<Q', memory(address, 8, f'coexist-hid-{idx}'))[0]
                for idx,address in enumerate(readers)]

    def hid_activity(before, delta):
        command('send-key', {'keys':[{'type':'qcode','data':'f10'}],'hold-time':60})
        command('input-send-event', {'events':[{'type':'rel','data':{'axis':'x','value':delta}}]})
        deadline = time.monotonic()+15
        while time.monotonic()<deadline:
            after = counters()
            if after[0]>=before[0]+2 and after[1]>before[1]:
                return
            time.sleep(.03)
        raise ValueError(f'USB dejó de entregar informes con AMD-Vi: {before} -> {after}')

    # The fixture owns the entire virtual machine. Quiesce other requesters
    # with PCI Command and keep their values to restore after the test.
    try:
        machine.pci(4, edu_idle_command, word=True)
        require(not machine.pci(4, word=True) & 4, 'EDU conserva bus mastering del firmware')
        pending = {rid: machine.pci(4, word=True, requester=rid) for rid in functions
                   if rid not in (EDU_REQUESTER,xhci)}
        if guest_dma:
            require(any(value & 4 for value in pending.values()), 'Falta el bus master para el rechazo inicial')
            guest_request(1,2)
            require(machine.read(AMDVI+24)==0 and machine.read(context+0xb68)==0,
                    'Ring 0 activó DMA con otro bus master presente')
        for rid,value in pending.items():
            if value & 4:
                disabled[rid] = value
                machine.pci(4, value & ~4, word=True, requester=rid)
                require(not machine.pci(4, word=True, requester=rid) & 4, 'Otro bus master sigue activo')
        if guest_dma:
            guest_request(1)
            require(machine.read(context+0xb68)==1 and machine.read(completion)==64,
                    'Ring 0 no confirmó las dos entradas DMA')
        else:
            machine.put_bytes(scratch, bytes(13*PAGE))
            leaf = map_pages(machine, edu_root, iter((edu_root+PAGE,)), [(iova,payload)])
            map_pages(machine, usb_root, iter((usb_root+PAGE,usb_root+2*PAGE)),
                      [(usb+i*PAGE,usb+i*PAGE) for i in range(pages)])
            for rid, root, domain in ((EDU_REQUESTER,edu_root,1),(xhci,usb_root,2)):
                machine.put_bytes(table+rid*32, struct.pack('<4Q',root|READ_WRITE|0x403,domain,0,0))
            machine.write(AMDVI, table | 1)
            machine.write(AMDVI+8, commands | 8<<56)
            machine.write(AMDVI+16, events | 8<<56)
            machine.write(AMDVI+24, 0x1005)
            for offset,rid in enumerate((EDU_REQUESTER,xhci)):
                publish_command(machine, offset*32, 2<<60 | rid, 0, offset+1,
                                command_ring=commands,completion=completion)
        require(machine.read(AMDVI+24) & 0x1005 == 0x1005, 'AMD-Vi no entró en traducción')
        require(machine.read(AMDVI)==table|1 and machine.read(table+EDU_REQUESTER*32+8)==1
                and machine.read(table+xhci*32+8)==2, 'Los solicitantes no recibieron dominios separados')
        machine.pci(4, edu_idle_command | 2, word=True)
        require(int(machine.command('readl',bar),16)==0x010000ed and not machine.read(bar+0x98) & 1,
                f'EDU no estaba listo en {bar:#x}')
        machine.pci(4, edu_idle_command | 6, word=True)
        machine.put_bytes(payload, data)
        machine.put_bytes(iova, sentinel)
        machine.put_bytes(iova+0x100, sentinel)
        machine.put_bytes(outside, sentinel)
        initial = counters()
        run_transfer(machine, command, bar, iova, EDU_BUFFER, len(data), 1)
        run_transfer(machine, command, bar, EDU_BUFFER, iova+0x100, len(data), 3,
                     lambda: hid_activity(initial,8))
        granted = counters()
        require(machine.get_bytes(payload+0x100,len(data)) == data and not machine.read(AMDVI+0x2018),
                'DMA concedido o USB produjo un resultado inesperado')
        require(machine.get_bytes(iova+0x100,len(data)) == sentinel, 'Cambió la RAM de la IOVA')
        run_transfer(machine, command, bar, EDU_BUFFER, outside, len(data), 3)
        tail, _ = faults(machine, 0, outside, len(data), event_log=events)
        require(machine.get_bytes(outside,len(data)) == sentinel, 'Cambió la página fuera del préstamo')
        if guest_dma:
            machine.pci(4,edu_idle_command | 2,word=True)
            guest_request(2)
            require(machine.read(context+0xb68)==2 and machine.read(completion)==96,
                    'Ring 0 no confirmó la invalidación')
            machine.pci(4,edu_idle_command | 6,word=True)
        else:
            machine.write(leaf, 0)
            publish_command(machine, 64, 3<<60 | 1<<32, iova, 3, command_ring=commands,completion=completion)
        machine.put_bytes(payload, sentinel)
        run_transfer(machine, command, bar, EDU_BUFFER, iova, len(data), 3,
                     lambda: hid_activity(granted,-8))
        revoked = counters()
        faults(machine, tail, iova, len(data), event_log=events)
        require(machine.get_bytes(payload,len(data)) == machine.get_bytes(iova,len(data)) == sentinel,
                'DMA revocado alteró la memoria')
    finally:
        failure = sys.exc_info()[1]
        machine.pci(4, edu_idle_command, word=True)
        if guest_dma:
            if machine.read(context+0xb68) in (1,2):
                try:
                    guest_request(3)
                    require(machine.read(context+0xb68)==3, 'Ring 0 no cerró el ensayo DMA')
                except (ValueError, RuntimeError) as cleanup_error:
                    if failure:
                        raise ValueError(f'{failure}; cierre: {cleanup_error}') from cleanup_error
                    raise
        else:
            machine.write(AMDVI+24, 0)
            for off in (0,8,16,0x2000,0x2008,0x2010,0x2018):
                machine.write(AMDVI+off, 0)
        for rid,value in disabled.items():
            machine.pci(4, value, word=True, requester=rid)
    require(not (machine.read(AMDVI+24) & 1 or machine.pci(4,word=True) & 4)
            and machine.pci(4,word=True,requester=xhci) & 4, 'Cierre DMA inesperado')
    return dict(AmdViCoexistVerified=True, DmaIssuer='Ring 0 guest' if guest_dma else 'QEMU qtest HOST',
                EduRequester=f'{EDU_REQUESTER:04x}', XhciRequester=f'{xhci:04x}',
                EduTransferredBytes=len(data), XhciIdentityPages=pages, ScratchPages=scratch_pages,
                ActiveBusMasterRejectedByGuest=guest_dma, GuestInvalidationVerified=guest_dma,
                UsbReportsDuringGrant=[b-a for a,b in zip(initial,granted)],
                UsbReportsAfterRevocation=[b-a for a,b in zip(granted,revoked)],
                BoundedDmaRejected=True, RevokedDmaRejected=True,
                TemporarilyQuiescedRequesters=[f'{rid:04x}' for rid in disabled])
