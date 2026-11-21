"""Verify the RTX firmware boot mappings with an AMD-Vi QEMU fixture."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from gsp_dma import (DEVICE_TABLE_PAGES, DOMAIN, PAGE, RELEASE, RID_AUDIO, RID_GRAPHICS,
                     aligned_payload, build_tables, load_firmware)
from qemu_dma import (AMDVI, COMMAND_RING, COMPLETION, EVENT_LOG, QTest,
                      publish_command, require, submit_transfer)


BRIDGE = 0x18
GRAPHICS_BAR = 0xe1000000
AUDIO_BAR = 0xe1100000
DEVICE_TABLE = 0x240000
ROOTS = 0x300000
BACKING = 0x04000000
IOVA = 0x08000000
EDU_BUFFER = 0x40000
CONTROL = 0x1005
INVALIDATE_DOMAIN = 0x7ffffffffffff003  # S and PDE bits, all pages.


def configure(machine, reply_iova, payload_bytes):
    machine.pci(0x18, 0x00292900, requester=BRIDGE)
    machine.pci(0x20, 0xe110e100, requester=BRIDGE)
    machine.pci(4, 2, requester=BRIDGE, word=True)
    for requester, bar in ((RID_GRAPHICS, GRAPHICS_BAR), (RID_AUDIO, AUDIO_BAR)):
        require(machine.pci(0, requester=requester)==0x11e81234,
                f'Falta dispositivo virtual {requester:04x}')
        machine.pci(0x10, bar, requester=requester)
        machine.pci(4, 2, requester=requester, word=True)
        require(int(machine.command('readl', bar),16)==0x010000ed, 'BAR virtual no responde')

    require(not machine.read(AMDVI+24), 'AMD-Vi inicial ya activo')
    require(reply_iova+PAGE<0x10000000 and
            BACKING+payload_bytes+PAGE<IOVA, 'Geometria DMA virtual fuera de la RAM del ensayo')
    machine.write(AMDVI, DEVICE_TABLE | (DEVICE_TABLE_PAGES-1))
    machine.write(AMDVI+8, COMMAND_RING | (8 << 56))
    machine.write(AMDVI+16, EVENT_LOG | (8 << 56))
    machine.write(AMDVI+24, CONTROL)
    require(machine.read(AMDVI+24)==CONTROL, 'AMD-Vi no confirmo control')
    for index, requester in enumerate((RID_GRAPHICS, RID_AUDIO, BRIDGE)):
        publish_command(machine, index*32, 2 << 60 | requester, 0, index+1)


def verify(machine, payload, layout, reply_iova, denied):
    configure(machine, reply_iova, len(payload))
    reply_phys = BACKING+len(payload)
    gap = reply_iova-PAGE
    sentinel = bytes([0xa5])*32
    marker = b'BMO-X2 testigo DMA GPU'.ljust(len(sentinel),b'!')
    for address in (reply_phys, gap, reply_iova):
        machine.put_bytes(address, sentinel)

    def master(requester, enabled):
        value = 6 if enabled else 2
        machine.pci(4, value, word=True, requester=requester)
        require(machine.pci(4, word=True, requester=requester)==value,
                f'No se verifico BME de {requester:04x}')

    def transfer(bar, source, target, direction, size=32):
        submit_transfer(machine,source,target,size,direction,bar=bar)
        machine.command('clock_step',101_000_000)
        require(not machine.read(bar+0x98)&1, 'EDU no termino el comando')

    tail = 0
    faults = {}

    def expect_fault(name, requester, iova):
        nonlocal tail
        end = machine.read(AMDVI+0x2018)
        require(tail < end < PAGE and (end-tail)%16==0,
                f'{name}: sin eventos AMD-Vi, cola {tail:#x} -> {end:#x}')
        observed = []
        for word,address in struct.iter_unpack('<2Q',machine.get_bytes(EVENT_LOG+tail,end-tail)):
            reported = word & 0xffff
            # The model can omit the PCI bus number in page fault reports.
            require(word>>60==2 and reported in (requester,requester & 0xff)
                    and (address==0 or iova<=address<iova+len(sentinel)),
                    f'{name}: evento AMD-Vi inesperado {word:#x} {address:#x}')
            observed.append((f'{reported:04x}',f'{address:x}'))
        tail = end
        faults[name] = dict(requester=f'{requester:04x}', event_count=len(observed),
                            raw_events=sorted(set(observed)))

    master(RID_GRAPHICS,True)
    try:
        offsets = (0, PAGE-16, layout['firmware_bytes']-32,
                   layout['signature_iova']-IOVA, layout['radix3_iova']-IOVA)
        for offset in offsets:
            transfer(GRAPHICS_BAR,IOVA+offset,EDU_BUFFER,1)
            transfer(GRAPHICS_BAR,EDU_BUFFER,reply_iova,3)
            require(machine.get_bytes(reply_phys,32)==payload[offset:offset+32] and
                    machine.get_bytes(reply_iova,32)==sentinel and not machine.read(AMDVI+0x2018),
                    f'Lectura DMA no coincide: desplazamiento {offset:#x}')
        transfer(GRAPHICS_BAR,EDU_BUFFER,IOVA,3)
        if machine.read(AMDVI+0x2018)!=tail:
            expect_fault('cached_firmware_write',RID_GRAPHICS,IOVA)
        cold = 2*PAGE
        transfer(GRAPHICS_BAR,EDU_BUFFER,IOVA+cold,3)
        expect_fault('firmware_write',RID_GRAPHICS,IOVA+cold)
        require(machine.get_bytes(BACKING,32)==payload[:32] and
                machine.get_bytes(BACKING+cold,32)==payload[cold:cold+32],
                'Escritura alcanzo firmware de solo lectura')
        transfer(GRAPHICS_BAR,EDU_BUFFER,gap,3)
        expect_fault('unmapped_gap',RID_GRAPHICS,gap)
        require(machine.get_bytes(gap,32)==sentinel, 'Escritura alcanzo el hueco entre reservas')

        received = hashlib.sha256()
        for offset in range(0,len(payload),PAGE):
            transfer(GRAPHICS_BAR,IOVA+offset,EDU_BUFFER,1,PAGE)
            transfer(GRAPHICS_BAR,EDU_BUFFER,reply_iova,3,PAGE)
            received.update(machine.get_bytes(reply_phys,PAGE))
        require(received.digest()==hashlib.sha256(payload).digest() and
                machine.get_bytes(reply_iova,32)==sentinel and machine.read(AMDVI+0x2018)==tail,
                'La transferencia DMA del firmware completo no coincide')
    finally:
        master(RID_GRAPHICS,False)

    # The sibling uses the same PCIe route and has its own requester.
    # Give it a distinctive buffer without granting access to GPU data.
    master(RID_AUDIO,True)
    try:
        prior_reply = machine.get_bytes(reply_phys,32)
        transfer(AUDIO_BAR,EDU_BUFFER,reply_iova,3)
        expect_fault('audio_reply_write',RID_AUDIO,reply_iova)
        require(machine.get_bytes(reply_phys,32)==prior_reply and
                machine.get_bytes(reply_iova,32)==sentinel, 'Audio altero el buffer de respuesta')
        transfer(AUDIO_BAR,IOVA,EDU_BUFFER,1)
        expect_fault('audio_firmware_read',RID_AUDIO,IOVA)
    finally:
        master(RID_AUDIO,False)

    # The device has stopped and BME is off before changing its DTE.
    machine.put_bytes(DEVICE_TABLE+RID_GRAPHICS*32,denied)
    publish_command(machine,96,3 << 60 | DOMAIN << 32,INVALIDATE_DOMAIN,4)
    publish_command(machine,128,2 << 60 | RID_GRAPHICS,0,5)
    require(machine.read(AMDVI+0x2018)==tail, 'Evento al invalidar el dominio')
    machine.put_bytes(reply_phys,marker)
    master(RID_GRAPHICS,True)
    try:
        transfer(GRAPHICS_BAR,EDU_BUFFER,reply_iova,3)
        expect_fault('revoked_reply_write',RID_GRAPHICS,reply_iova)
        require(machine.get_bytes(reply_phys,32)==marker and
                machine.get_bytes(reply_iova,32)==sentinel, 'El DMA revocado altero RAM')
        transfer(GRAPHICS_BAR,IOVA,EDU_BUFFER,1)
        expect_fault('revoked_firmware_read',RID_GRAPHICS,IOVA)
    finally:
        master(RID_GRAPHICS,False)
    machine.write(AMDVI+24,0)
    require(not machine.read(AMDVI+24), 'AMD-Vi virtual no cerro')
    return dict(verified_dma_samples=len(offsets), verified_dma_pages=len(payload)//PAGE,
                compared_dma_bytes=len(payload), received_dma_sha256=received.hexdigest(),
                cached_firmware_write_blocked=True, bus_master_disabled=True,
                revoked_domain=DOMAIN, invalidation_verified=True, dma_faults=faults)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('firmware_directory', type=Path)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    args = parser.parse_args()
    container = load_firmware(args.firmware_directory)
    payload, layout = aligned_payload(container, IOVA)
    devices, tree, reply_iova, denied = build_tables(
        DEVICE_TABLE, ROOTS, BACKING, IOVA, layout['read_only_pages'])

    with tempfile.TemporaryDirectory(prefix='bmo-gsp-dma-') as directory:
        launch = [str(args.qemu),'-machine','q35','-accel','qtest','-nodefaults','-display','none',
                  '-monitor','none','-serial','none','-m','256','-device','amd-iommu,dma-remap=on',
                  '-device','pcie-root-port,id=gpu-slot,addr=03.0,chassis=3,slot=3',
                  '-device','edu,bus=gpu-slot,addr=00.0,multifunction=on',
                  '-device','edu,bus=gpu-slot,addr=00.1','-qtest','stdio','-qtest-log','none']
        for name, address, data in (('devices',DEVICE_TABLE,devices), ('tree',ROOTS,tree),
                                    ('firmware',BACKING,payload)):
            file = Path(directory)/f'{name}.bin'
            file.write_bytes(data)
            launch += ['-device',f'loader,file={file},addr={address:#x},force-raw=on']
        with subprocess.Popen(launch,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,text=True,encoding='ascii') as process:
            try:
                result = verify(QTest(process),payload,layout,reply_iova,denied)
            finally:
                process.terminate()
                process.wait(timeout=5)
    version = subprocess.check_output([args.qemu,'--version'],text=True).splitlines()[0]
    print(json.dumps(dict(schema=1, evidence='QEMU qtest: AMD-Vi with two emulated PCIe functions',
                          qemu=version, release=RELEASE, graphics_requester=f'{RID_GRAPHICS:04x}',
                          audio_requester=f'{RID_AUDIO:04x}', firmware_container_sha256=hashlib.sha256(container).hexdigest(),
                          aligned_payload_sha256=hashlib.sha256(payload).hexdigest(),
                          writable_pages=1, device_table_pages=DEVICE_TABLE_PAGES, table_tree_pages=len(tree)//PAGE,
                          guest_kernel_executed=False, physical_gpu_verified=False,
                          **layout, **result),indent=2))


if __name__=='__main__':
    main()
