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
ROUTED_TABLE_PAGES = 512


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


def verify_coexistence(machine, command, memory, context, symbols, *,
                       guest_dma=False, storage=False, routed=False, nvme=False,
                       guest_nvme=False, guest_ahci=False, gsp_dma=False):
    """Run at the first frozen desktop frame. Return with the guest paused."""
    scratch_pages = 18 if storage else 14 if guest_dma else 13
    if nvme:
        require(storage and guest_dma and (not routed or gsp_dma),
                'NVMe requiere el banco de cuatro dominios')
        scratch_pages = 31
    if routed:
        require(storage and guest_dma, 'El ensayo en buses altos requiere los tres dominios del invitado')
        scratch_pages += ROUTED_TABLE_PAGES
    if gsp_dma:
        require(guest_ahci and guest_nvme, 'El firmware requiere el banco con ambos controladores del invitado')
    scratch, usb, pages = dma_ranges(memory, context, scratch_pages)
    devices = command('query-pci')
    require(len(devices)==1, 'Segmentos PCI QEMU fuera del ensayo')

    def pci_functions(entries):
        for entry in entries:
            yield entry['bus']*256 + entry['slot']*8 + entry['function'], entry
            yield from pci_functions(entry.get('pci_bridge', {}).get('devices', []))

    functions = dict(pci_functions(devices[0]['devices']))
    bridges = {rid for rid,entry in functions.items() if 'pci_bridge' in entry}
    require(bridges==({0x38,0x40} if routed else set()), 'Topología QEMU fuera del ensayo')
    edu, = (rid for rid, entry in functions.items() if entry['qdev_id'] == 'bmo-edu')
    if routed:
        children = functions[0x40]['pci_bridge']['devices']
        require(0x2900<=edu<ROUTED_TABLE_PAGES*128 and functions[edu] in children,
                f'EDU fuera del bus alto esperado: {edu:04x}')
        if gsp_dma:
            require(edu==0x2900 and functions.get(0x2901) in children,
                    'El ensayo del firmware requiere las dos funciones PCIe 29:00')
    else:
        require(edu==EDU_REQUESTER, 'EDU debe estar en el bus raiz del perfil base')
    xhci, = (rid for rid, entry in functions.items() if entry['qdev_id'] == 'bmo-native-xhci')
    if storage:
        from amdvi_ahci import REQUESTER, read_sector, verify_guest_read
        ahci = functions[REQUESTER]
        ahci_bar, = (region['address'] for region in ahci['regions'] if region['bar']==5)
        pci_bar = machine.pci(0x24,requester=REQUESTER)
        require(ahci['qdev_id']=='bmo-dma-ahci' and machine.pci(0,requester=REQUESTER)==0x29228086
                and ahci_bar == pci_bar & ~15 and 0x80000000 <= ahci_bar < 0x100000000,
                f'AHCI fuera del laboratorio: {ahci["id"]}, BAR5 {ahci_bar:#x}, PCI {pci_bar:#x}')
    if nvme:
        import amdvi_nvme
        nvme_rid = amdvi_nvme.REQUESTER
        device = functions[nvme_rid]
        region, = (entry for entry in device['regions'] if entry['bar']==0)
        nvme_bar, nvme_size = region['address'], region['size']
        pci_bar = machine.pci(0x10,requester=nvme_rid) | machine.pci(0x14,requester=nvme_rid)<<32
        require(device['qdev_id']=='bmo-nvme' and machine.pci(0,requester=nvme_rid)==0x00101b36
                and 0x80000000<=nvme_bar<nvme_bar+nvme_size<=1<<52
                and nvme_bar==pci_bar & ~15 and pci_bar&7==4,
                f'BAR0 NVMe fuera del banco: {device["qdev_id"]}, QMP {nvme_bar:#x}, PCI {pci_bar:#x}')
    def edu_pci(register, value=None, *, word=False):
        return machine.pci(register, value, word=word, requester=edu)

    require(edu_pci(0) == 0x11e81234 and machine.pci(4, word=True, requester=xhci) & 4,
            'Falta EDU o xHCI no está activo')
    disabled = {}
    edu_command = edu_pci(4, word=True)
    bar_register = edu_pci(0x10)
    bar, = (region['address'] for region in functions[edu]['regions'] if region['bar']==0)
    require(bar_register == bar and 0x80000000 <= bar < 0x100000000 and bar % 0x100000 == 0,
            'BAR0 de EDU difiere del recurso asignado por OVMF')
    if routed:
        denied_requester = 0x2901 if gsp_dma else EDU_REQUESTER
        denied = functions[denied_requester]
        denied_bar, = (region['address'] for region in denied['regions'] if region['bar']==0)
        require(denied['qdev_id']=='bmo-edu-denied'
                and machine.pci(0x10,requester=denied_requester)==denied_bar
                and 0x80000000<=denied_bar<0x100000000, 'Falta el EDU sin dominio')
    require(not any(machine.read(AMDVI + off) for off in (0,8,16,24,0x2020)), 'AMD-Vi ya estaba activo')
    edu_idle_command = edu_command & ~4
    table, edu_root, usb_root = scratch, scratch+2*PAGE, scratch+4*PAGE
    if routed:
        table += (31 if nvme else 18)*PAGE
    table_pages = ROUTED_TABLE_PAGES if routed else 2
    startup_tail = 32*len(functions) if routed else 128 if nvme else 96 if storage else 64
    commands, events, completion = (scratch+offset*PAGE for offset in (7,8,9))
    payload, iova, outside = (scratch+offset*PAGE for offset in (10,11,12))
    sentinel, data = bytes([0xa5])*8, b'BMOX2DMA'
    if gsp_dma:
        gsp_image, gsp_signature, gsp_radix, gsp_root = struct.unpack('<4Q',
            memory(context+0x818,32,'coexist-gsp-ranges'))
        gsp_iova = 0x08000000
        proof_sources = (gsp_iova,gsp_iova+gsp_signature-gsp_image,gsp_radix)
        reply_pde = gsp_root+(iova>>21)*8
        require(machine.read(reply_pde)==0, 'El testigo solapa una IOVA del firmware')
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
                f'control={machine.read(AMDVI+24):#x}, lectura de cierre={machine.read(context+0xb70):#x}, '
                f'paso NVMe={machine.read(context+0xbd0) if guest_nvme else 0}, '
                f'paso AHCI={machine.read(context+0xbe0) if guest_ahci else 0}')
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

    def read_nvme(delta):
        before_read = counters()
        activity = lambda: hid_activity(before_read,delta)
        if guest_nvme:
            return amdvi_nvme.verify_guest_read(machine,command,nvme_bar,scratch,context,guest_request,activity)
        return amdvi_nvme.read_sector(machine,command,nvme_bar,nvme_size,scratch,activity)

    def read_ahci(delta):
        before_read = counters()
        activity = lambda: hid_activity(before_read,delta)
        if guest_ahci:
            return verify_guest_read(machine,command,ahci_bar,scratch,context,guest_request,activity)
        return read_sector(machine,command,ahci_bar,scratch,activity)

    def denied_edu_write(prime):
        pci_command = machine.pci(4,word=True,requester=denied_requester)
        require(not pci_command & 4,'El testigo EDU tiene BME activo')
        machine.pci(4,pci_command | 6,word=True,requester=denied_requester)
        try:
            require(machine.pci(4,word=True,requester=denied_requester) & 4
                    and int(machine.command('readl',denied_bar),16)==0x010000ed,
                    'El segundo EDU no responde')
            if prime:
                machine.put_bytes(outside+0x100,data)
                run_transfer(machine,command,denied_bar,outside+0x100,EDU_BUFFER,len(data),1)
            machine.put_bytes(outside,sentinel)
            run_transfer(machine,command,denied_bar,EDU_BUFFER,outside,len(sentinel),3)
            return machine.get_bytes(outside,len(data))
        finally:
            machine.pci(4,pci_command,word=True,requester=denied_requester)

    def reported_requester(offset, requester):
        if not routed:
            return requester
        # QEMU can emit devfn without the upstream bus. The DTE and the
        # transfer are independently checked against the full requester.
        reported = machine.read(events+offset) & 0xffff
        require(reported in (requester, requester & 0xff),
                f'Solicitante inesperado en el evento AMD-Vi: {reported:04x}')
        return reported

    # The fixture owns the entire virtual machine. Quiesce other requesters
    # with PCI Command and keep their values to restore after the test.
    try:
        edu_pci(4, edu_idle_command, word=True)
        require(not edu_pci(4, word=True) & 4, 'EDU conserva bus mastering del firmware')
        pending = {rid: machine.pci(4, word=True, requester=rid) for rid in functions
                   if rid not in (edu,xhci) and rid not in bridges}
        if guest_dma:
            require(any(value & 4 for value in pending.values()), 'Falta el bus master para el rechazo inicial')
            guest_request(1,2)
            require(machine.read(AMDVI+24)==0 and machine.read(context+0xb68)==0,
                    'Ring 0 activó DMA con otro bus master presente')
        if guest_nvme:
            guest_request(4,1)
            require(machine.read(context+0xbc0)==0 and machine.read(context+0xbd0)==0,
                    'Ring 0 inicio NVMe sin dominio activo')
        if guest_ahci:
            guest_request(5,1)
            require(machine.read(context+0xbd8)==0 and machine.read(context+0xbe0)==0,
                    'Ring 0 inicio AHCI sin dominio activo')
        if gsp_dma:
            guest_request(8,1)
            require(not edu_pci(4,word=True)&4, 'Ring 0 habilito BME sin dominio')
        if nvme:
            inherited = pending.pop(nvme_rid)
            require(inherited&6==6, 'OVMF no dejo NVMe inicializado')
            if not guest_ahci:
                nvme_shutdown = amdvi_nvme.shutdown(machine,command,nvme_bar)
                require(nvme_shutdown is not None, 'NVMe no confirmo el cierre de las colas de UEFI')
                machine.pci(4,inherited & ~4,word=True,requester=nvme_rid)
                require(machine.pci(4,word=True,requester=nvme_rid)==inherited & ~4,
                        'NVMe conserva BME tras cerrar las colas de UEFI')
        if guest_ahci:
            ahci_inherited = pending.pop(REQUESTER)
        for rid,value in pending.items():
            if value & 4:
                disabled[rid] = value
                machine.pci(4, value & ~4, word=True, requester=rid)
                require(not machine.pci(4, word=True, requester=rid) & 4, 'Otro bus master sigue activo')
        if guest_ahci:
            guest_request(6)
            nvme_shutdown = machine.read(context+0xbe8)
            require(nvme_shutdown&0x4e==8 and machine.pci(4,word=True,requester=nvme_rid)==inherited&~4
                    and not amdvi_nvme.read32(machine,nvme_bar,0x14)&0xc001
                    and not amdvi_nvme.read32(machine,nvme_bar,0x1c)&0x43,
                    f'Ring 0 no confirmo el cierre del NVMe heredado: ack={nvme_shutdown:#x}, '
                    f'PCI={machine.pci(4,word=True,requester=nvme_rid):#x}/{inherited&~4:#x}, '
                    f'CC={amdvi_nvme.read32(machine,nvme_bar,0x14):#x}, '
                    f'CSTS={amdvi_nvme.read32(machine,nvme_bar,0x1c):#x}')
            guest_request(7)
            port_states = [int(machine.command('readl',ahci_bar+0x118+0x80*port),16) for port in range(6)]
            require(machine.read(context+0xbf0)==1 and not any(cmd&0xc011 for cmd in port_states)
                    and machine.pci(4,word=True,requester=REQUESTER)==ahci_inherited&~4
                    and not machine.read(AMDVI+24), 'Ring 0 no confirmo el cierre del AHCI heredado')
        if routed:
            require(denied_edu_write(prime=True)==data,'El testigo EDU no transfirio con AMD-Vi apagado')
        if guest_dma:
            guest_request(1)
            require(machine.read(context+0xb68)==1 and machine.read(completion)==startup_tail,
                    'Ring 0 no confirmó las entradas DMA')
            if routed:
                queued = struct.iter_unpack('<4Q',memory(commands,startup_tail,'routed-invalidations'))
                require(machine.read(context+0xb78)==edu and
                        [low for low,_,_,_ in queued]==[(2<<60)|rid for rid in sorted(functions)],
                        'Los BDF enumerados e invalidados por Ring 0 difieren de QMP')
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
        require(machine.read(AMDVI)==table|(table_pages-1) and machine.read(table+edu*32+8)==1
                and machine.read(table+xhci*32+8)==2, 'Los solicitantes no recibieron dominios separados')
        if gsp_dma:
            require(machine.read(table+edu*32)==gsp_root|READ_WRITE|0x403 and
                    machine.read(reply_pde)==(scratch+3*PAGE)|READ_WRITE|0x201,
                    'Ring 0 no vinculo el arbol preparado al solicitante')
        if routed or gsp_dma:
            empty_root = edu_root if gsp_dma else scratch
            default_dte = (empty_root | READ_WRITE | 0x403,0,0,0)
            entries = struct.iter_unpack('<4Q', memory(table,table_pages*PAGE,'blocked-device-table'))
            admitted = {edu,xhci,REQUESTER}
            if nvme:
                admitted.add(nvme_rid)
            require(all(entry==default_dte for rid,entry in enumerate(entries) if rid not in admitted)
                    and memory(empty_root,PAGE,'blocked-empty-root')==bytes(PAGE),
                    'Un solicitante sin dominio tiene acceso por defecto')
        storage_proof = {}
        if storage:
            if guest_ahci:
                guest_request(6,1)
                guest_request(7,1)
            require(machine.read(table+REQUESTER*32+8)==3, 'Falta el dominio separado AHCI')
            first_sector = read_ahci(8)
        if nvme:
            first_nvme = read_nvme(-8)
        edu_pci(4, edu_idle_command | 2, word=True)
        require(int(machine.command('readl',bar),16)==0x010000ed and not machine.read(bar+0x98) & 1,
                f'EDU no estaba listo en {bar:#x}')
        if gsp_dma:
            guest_request(8)
            require(edu_pci(4,word=True)==(edu_idle_command | 6) and machine.read(context+0xb68)==1,
                    'Ring 0 no habilito BME despues de validar el dominio')
        else:
            edu_pci(4, edu_idle_command | 6, word=True)
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
        tail = 0
        gsp_proof = {}
        if gsp_dma:
            for source in proof_sources:
                physical = gsp_image+source-gsp_iova
                expected = machine.get_bytes(physical,PAGE)
                machine.put_bytes(payload, bytes(value ^ 0xff for value in expected))
                run_transfer(machine,command,bar,source,EDU_BUFFER,PAGE,1)
                run_transfer(machine,command,bar,EDU_BUFFER,iova,PAGE,3)
                require(machine.get_bytes(payload,PAGE)==expected and not machine.read(AMDVI+0x2018),
                        f'El DMA del firmware difiere en IOVA {source:#x}')
            cold = gsp_iova+2*PAGE
            before_write = machine.get_bytes(gsp_image+2*PAGE,32)
            run_transfer(machine,command,bar,EDU_BUFFER,cold,32,3)
            tail,_ = faults(machine,tail,cold,32,event_log=events,
                            requester=reported_requester(tail,edu))
            require(machine.get_bytes(gsp_image+2*PAGE,32)==before_write,
                    'EDU escribio en el firmware de solo lectura')
            rmargs = machine.read(context+0x838)
            if rmargs:
                from host.gpu.NVIDIA.gsp_args import STATUS_OFFSET

                page_mask = ((1<<52)-1) & -PAGE
                queue_leaf = machine.read(gsp_root+(rmargs>>21)*8) & page_mask
                queue_base = machine.read(queue_leaf) & page_mask
                status_offset = PAGE+STATUS_OFFSET
                status_iova, status_ram = rmargs+status_offset, queue_base+status_offset
                require(machine.get_bytes(status_ram,len(data))==bytes(len(data)),
                        'La cola GSP de retorno no estaba limpia')
                machine.put_bytes(payload,data)
                run_transfer(machine,command,bar,iova,EDU_BUFFER,len(data),1)
                run_transfer(machine,command,bar,EDU_BUFFER,status_iova,len(data),3)
                require(machine.get_bytes(status_ram,len(data))==data and machine.read(AMDVI+0x2018)==tail,
                        'El DMA no pudo escribir la cola GSP de retorno')
                before_args = machine.get_bytes(queue_base,len(data))
                run_transfer(machine,command,bar,EDU_BUFFER,rmargs,len(data),3)
                tail,_ = faults(machine,tail,rmargs,len(data),event_log=events,
                                requester=reported_requester(tail,edu))
                require(machine.get_bytes(queue_base,len(data))==before_args,
                        'El DMA modifico RMARGS de solo lectura')
                gsp_proof.update(GspStatusQueueDmaWriteVerified=True,GspRmargsDmaWriteDenied=True)
                libos = machine.read(context+0x840)
                if libos:
                    libos_ram = queue_base+libos-rmargs
                    before_libos = machine.get_bytes(libos_ram,len(data))
                    run_transfer(machine,command,bar,EDU_BUFFER,libos,len(data),3)
                    tail,_ = faults(machine,tail,libos,len(data),event_log=events,
                                    requester=reported_requester(tail,edu))
                    require(machine.get_bytes(libos_ram,len(data))==before_libos,
                            'El DMA modifico los argumentos de LIBOS')
                    run_transfer(machine,command,bar,EDU_BUFFER,libos+PAGE,len(data),3)
                    require(machine.get_bytes(libos_ram+PAGE,len(data))==data
                            and machine.read(AMDVI+0x2018)==tail,
                            'El DMA no pudo escribir en LOGINIT')
                    gsp_proof.update(GspLibosArgumentWriteDenied=True,GspLibosLogWriteVerified=True)
                boot_iova = machine.read(context+0x848)
                if boot_iova:
                    boot_entry = (boot_iova-rmargs)//PAGE
                    boot_ram = machine.read(queue_leaf+boot_entry*8) & page_mask
                    signed_sample = machine.get_bytes(boot_ram,PAGE)
                    machine.put_bytes(payload,bytes(value ^ 0xff for value in signed_sample))
                    run_transfer(machine,command,bar,boot_iova,EDU_BUFFER,PAGE,1)
                    run_transfer(machine,command,bar,EDU_BUFFER,iova,PAGE,3)
                    require(machine.get_bytes(payload,PAGE)==signed_sample and machine.read(AMDVI+0x2018)==tail,
                            'La lectura DMA del monitor firmado difiere')
                    # Use a page that this requester has not read yet, as in
                    # the firmware-image fault test above.
                    cold = boot_iova+PAGE
                    before_boot_write = machine.get_bytes(boot_ram+PAGE,len(data))
                    run_transfer(machine,command,bar,EDU_BUFFER,cold,len(data),3)
                    tail,_ = faults(machine,tail,cold,len(data),event_log=events,
                                    requester=reported_requester(tail,edu))
                    require(machine.get_bytes(boot_ram+PAGE,len(data))==before_boot_write,
                            'El DMA modifico el monitor firmado')
                    gsp_proof.update(GspBootChainReadVerified=True,GspBootChainWriteDenied=True)
        run_transfer(machine, command, bar, EDU_BUFFER, outside, len(data), 3)
        fault_rid = reported_requester(tail,edu)
        tail, _ = faults(machine, tail, outside, len(data), event_log=events, requester=fault_rid)
        require(machine.get_bytes(outside,len(data)) == sentinel, 'Cambió la página fuera del préstamo')
        if guest_dma:
            revoke_start = startup_tail
            if not gsp_dma:
                edu_pci(4,edu_idle_command | 2,word=True)
            else:
                require(edu_pci(4,word=True)&4 and not machine.read(bar+0x98)&1,
                        'La prueba de revocacion necesita BME activo y la transferencia terminada')
                control = machine.read(AMDVI+24)
                # Keep translation active and withhold command completion.
                machine.write(AMDVI+24,control & ~0x1000)
                guest_request(2,3)
                revoke_start += 32
                queued = machine.get_bytes(commands+startup_tail,32)
                require(not edu_pci(4,word=True)&4 and machine.read(context+0xb68)==1
                        and machine.read(AMDVI+0x2008)==revoke_start and machine.read(completion)==startup_tail
                        and machine.read(table+edu*32)==default_dte[0],
                        'Una revocacion sin confirmacion debe cerrar BME sin liberar las reservas')
                guest_request(2,3)
                require(machine.read(AMDVI+0x2008)==revoke_start
                        and machine.get_bytes(commands+startup_tail,32)==queued,
                        'El reintento sobreescribio un comando pendiente')
                machine.write(AMDVI+24,control)
                machine.write(AMDVI+0x2008,revoke_start)
                require(machine.read(completion)==revoke_start, 'La cola DMA no se recupero')
                guest_request(8,3)
                require(not edu_pci(4,word=True)&4, 'Se reabrio BME con DTE retirada')
                gsp_proof['GspIncompleteRevocationClosedAndPinned']=True
            guest_request(2)
            revoke_bytes = 64 if gsp_dma else 32
            require(machine.read(context+0xb68)==2 and machine.read(completion)==revoke_start+revoke_bytes,
                    'Ring 0 no confirmó la invalidación')
            if gsp_dma:
                require(edu_pci(4,word=True)==(edu_idle_command | 2), 'Ring 0 dejo BME activo al revocar')
                guest_request(8,1)
                require(not edu_pci(4,word=True)&4, 'Ring 0 reabrio un dominio revocado')
                first, _, _, _, second, address, _, _ = struct.unpack(
                    '<8Q', machine.get_bytes(commands+revoke_start,revoke_bytes))
                require(first==(2<<60 | edu) and second==(3<<60 | 1<<32) and address==0x7ffffffffffff003,
                        'La invalidacion debe retirar primero la DTE y luego todas las paginas del dominio')
                gsp_proof.update(GspBusMasterGrantedByRing0=True,GspBusMasterClosedByRing0=True,
                                 GspDteThenDomainInvalidationVerified=True,GspReopenRejected=True)
            # qtest alone reopens BME as an adversarial probe of the revoked DTE.
            edu_pci(4,edu_idle_command | 6,word=True)
        else:
            machine.write(leaf, 0)
            publish_command(machine, 64, 3<<60 | 1<<32, iova, 3, command_ring=commands,completion=completion)
        machine.put_bytes(payload, sentinel)
        run_transfer(machine, command, bar, EDU_BUFFER, iova, len(data), 3,
                     lambda: hid_activity(granted,-8))
        revoked = counters()
        tail,_ = faults(machine, tail, iova, len(data), event_log=events, requester=fault_rid)
        require(machine.get_bytes(payload,len(data)) == machine.get_bytes(iova,len(data)) == sentinel,
                'DMA revocado alteró la memoria')
        if gsp_dma:
            require(machine.read(reply_pde)==0 and machine.read(table+edu*32)==default_dte[0]
                    and machine.read(table+edu*32+8)==0, 'La entrada del firmware sigue activa')
            run_transfer(machine,command,bar,gsp_iova,EDU_BUFFER,32,1)
            faults(machine,tail,gsp_iova,32,event_log=events,
                   requester=reported_requester(tail,edu),access=1)
            gsp_proof.update(GspDmaCoexistenceVerified=True,GspDmaReadSamples=len(proof_sources),
                             GspDmaSampleBytes=PAGE,GspFirmwareWriteDenied=True,
                             GspFirmwareDmaRevoked=True,GspUnassignedDtesDenied=True)
        if guest_ahci:
            guest_request(5,2)
            require(machine.read(context+0xbd8)==1, 'Ring 0 leyo AHCI con EDU activo')
        if guest_nvme:
            # Wait until the revoked EDU transfer is finished and reject
            # both disk operations until EDU loses bus mastering again.
            guest_request(4,2)
            require(machine.read(context+0xbc0)==1, 'Ring 0 leyo NVMe con EDU activo')
            edu_pci(4,edu_idle_command | 2,word=True)
        if storage:
            second_sector = read_ahci(-8)
            require(first_sector==second_sector, 'El sector cambio despues de revocar EDU')
            storage_proof = dict(AhciTranslatedReadsVerified=True, AhciRequester=f'{REQUESTER:04x}',
                                 AhciDomain=3, AhciSectorSHA256=first_sector,
                                 AhciBytesPerRead=512, AhciReadsVerified=2,
                                 AhciReadAfterEduRevocation=True, PhysicalStorageTested=False,
                                 AhciQueueOwner='Ring 0 guest' if guest_ahci else 'QEMU qtest HOST',
                                 AhciRejectedWithoutDomain=guest_ahci, AhciRejectedWithEduBme=guest_ahci,
                                 GuestStorageHandoff=guest_ahci)
        if nvme:
            second_nvme = read_nvme(8)
            require(first_nvme==second_nvme, 'El sector NVMe cambio despues de revocar EDU')
            storage_proof.update(NvmeTranslatedReadsVerified=True,NvmeDomain=4,NvmeRequester=f'{nvme_rid:04x}',
                                 NvmeSectorSHA256=first_nvme,NvmeBytesPerRead=512,NvmeReadsVerified=2,
                                 NvmeFirmwareShutdownStatus=nvme_shutdown,
                                 NvmeQueueOwner='Ring 0 guest' if guest_nvme else 'QEMU qtest HOST',
                                 NvmeRejectedWithoutDomain=guest_nvme,
                                 NvmeRejectedWithEduBme=guest_nvme,
                                 NvmeIovaPages=5,NvmeReadAfterEduRevocation=True)
        if routed:
            tail = machine.read(AMDVI+0x2018)
            require(denied_edu_write(prime=False)==sentinel,'Un solicitante sin dominio modifico RAM')
            faults(machine,tail,outside,len(sentinel),event_log=events,
                   requester=reported_requester(tail,denied_requester))
            if gsp_dma:
                gsp_proof.update(GspSiblingDmaDenied=True,GspSiblingRequester=f'{denied_requester:04x}')
    finally:
        failure = sys.exc_info()[1]
        edu_pci(4, edu_idle_command, word=True)
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
    require(not (machine.read(AMDVI+24) & 1 or edu_pci(4,word=True) & 4)
            and machine.pci(4,word=True,requester=xhci) & 4, 'Cierre DMA inesperado')
    routed_proof = dict(RoutedDmaVerified=True, DeviceTablePages=table_pages,
                        EduDteByteOffset=edu*32, FaultRequesterReported=f'{fault_rid:04x}',
                        FaultRequesterIncludesBus=fault_rid==edu,
                        DefaultDeniedDteVerified=True,
                        PresentRequestersInvalidated=len(functions),
                        UnassignedRequesterBlocked=f'{denied_requester:04x}') if routed else {}
    return dict(AmdViCoexistVerified=True, DmaIssuer='Ring 0 guest' if guest_dma else 'QEMU qtest HOST',
                EduRequester=f'{edu:04x}', XhciRequester=f'{xhci:04x}',
                EduTransferredBytes=len(data), XhciIdentityPages=pages, ScratchPages=scratch_pages,
                ActiveBusMasterRejectedByGuest=guest_dma, GuestInvalidationVerified=guest_dma,
                UsbReportsDuringGrant=[b-a for a,b in zip(initial,granted)],
                UsbReportsAfterRevocation=[b-a for a,b in zip(granted,revoked)],
                BoundedDmaRejected=True, RevokedDmaRejected=True,
                TemporarilyQuiescedRequesters=[f'{rid:04x}' for rid in disabled],
                **storage_proof, **routed_proof, **gsp_proof)
