"""Observe the actual native UI engine, presentation, ULTRA-J action and shutdown."""
import hashlib
import json
from pathlib import Path
import struct
import time
from cpu_config import register
from desktop_session_capture import verify_external_rejection


def verify_gsp_reservation(memory, context, expected, case):
    base, length, status, prepared, firmware, signature = struct.unpack(
        '<QQIIQQ', memory(context+0x800,40,'gsp-handoff'))
    detached = expected.get('detached_dma', False)
    queues = expected.get('queues', False)
    libos = expected.get('libos', False)
    boot_chain = expected.get('boot_chain')
    wpr_page = expected.get('wpr_page',False)
    fwsec = expected.get('fwsec')
    radix, dma_root = struct.unpack('<QQ', memory(context+0x828,16,'gsp-dma-handoff')) if detached else (0,0)
    rmargs, = struct.unpack('<Q',memory(context+0x838,8,'gsp-rmargs')) if queues else (0,)
    libos_iova, = struct.unpack('<Q',memory(context+0x840,8,'gsp-libos')) if libos else (0,)
    boot_iova, = struct.unpack('<Q',memory(context+0x848,8,'gsp-boot-chain')) if boot_chain else (0,)
    wpr_iova, = struct.unpack('<Q',memory(context+0x8f0,8,'gsp-wpr-iova')) if wpr_page else (0,)
    fuse, fwsec_iova = struct.unpack('<QQ',memory(context+0x8f8,16,'gsp-fwsec')) if fwsec else (0,0)
    if case == 'amdvi-missing':
        if status!=1 or any((base,length,prepared,firmware,signature,radix,dma_root,rmargs,libos_iova,
                             boot_iova,wpr_iova,fuse,fwsec_iova)):
            raise ValueError('Missing GSP file left a reservation')
        return {}
    reserved = (length+4096)//4096*4096
    prepared_bytes = 0
    if detached:
        image_pages = expected['layout']['sections']['.fwimage']['bytes']//4096
        directory_pages = 2+(image_pages+511)//512
        payload_pages = image_pages+1+directory_pages
        tree_pages = 1+(payload_pages+511)//512
        prepared_bytes = (payload_pages+tree_pages)*4096
    if queues:
        from host.gpu.NVIDIA.gsp_args import GSPMEM_PAGES, encode

        queue_iova = 0x0a000000
        queue_pages = 1+GSPMEM_PAGES
        queue_bytes = queue_pages*4096
        prepared_bytes += queue_bytes+4096
        libos_bytes = 0
        if libos:
            from host.gpu.NVIDIA.gsp_libos import LIBOS_PAGES, encode as encode_libos

            libos_bytes = LIBOS_PAGES*4096
            prepared_bytes += libos_bytes
        if boot_chain:
            prepared_bytes += boot_chain['pages']*4096
        if wpr_page:
            prepared_bytes += 4096
        if fwsec:
            prepared_bytes += fwsec['pages']*4096
    reserved = max(reserved, prepared_bytes)
    if (status!=5 or length!=expected['bytes'] or not 0x100000<=base<=0x10000000-reserved
            or base%4096):
        raise ValueError('Invalid GSP reservation in the handoff')
    map_length, stride = struct.unpack('<Q8xQ', memory(context+0x50,24,'gsp-map-geometry'))
    if not (40<=stride<=256 and 0<map_length<=65536 and map_length%stride==0):
        raise ValueError('Invalid final EFI map')
    memmap = memory(context+0x1000,map_length,'gsp-efi-map')
    descriptors = (struct.unpack_from('<I4xQQQ',memmap,offset)
                   for offset in range(0,len(memmap),stride))
    if not any(kind==2 and start<=base and base+reserved<=start+pages*4096
               for kind,start,_,pages in descriptors):
        raise ValueError('GSP data is not reserved in the final EFI map')
    for index in range(base>>21, ((base+reserved-1)>>21)+1):
        pde, = struct.unpack('<Q', memory(context+0x15000+index*8,8,'gsp-identity-pde'))
        if pde&0x85!=0x81 or pde&0x000fffffffe00000!=index<<21:
            raise ValueError('GSP reservation is outside supervisor identity memory')
    image = memory(base,reserved,'gsp-resident')
    if expected.get('prepare'):
        sections = expected['layout']['sections']
        size = sections['.fwimage']['bytes']
        ready = 5 if libos else 4 if queues else 3 if detached else 2
        if (prepared,firmware,signature)!=(ready,base,base+size):
            raise ValueError('Ring 0 GSP preparation pointers or status differ')
        if (hashlib.sha256(image[:size]).hexdigest()!=sections['.fwimage']['sha256'] or
                hashlib.sha256(image[size:size+4096]).hexdigest()!=sections['.fwsignature_ga10x']['sha256']):
            raise ValueError('Ring 0 altered the signed firmware or signature')
        used = size+4096
        result = dict(GspResidentVerified=True,GspResidentBytes=length,GspReservedPages=reserved//4096,
                      GspPreparedByRing0=True,GspPreparedPages=(size//4096)+1)
        if expected.get('physical_tables'):
            if memory(context+0x908,4,'physical-dte-status')!=b'\x01\0\0\0':
                raise ValueError('Ring 0 did not build the detached physical DTE')
            table=base+reserved
            deny=table+0x200000
            usb_root=deny+4096
            rows=memory(table,0x200000,'physical-dte')
            rw=0x6000000000000403
            for rid, row in enumerate(struct.iter_unpack('<4Q',rows)):
                target,domain=(dma_root,5) if rid==0x2900 else (usb_root,2) if rid==0x2b03 else (deny,0)
                if row!=(target|rw,domain,0,0):
                    raise ValueError(f'Physical DTE differs for requester {rid:#06x}')
            result['PhysicalDteBuiltDetached']=True
        if expected.get('physical_mmio_test'):
            dte_base, transaction = struct.unpack(
                '<QQ',memory(context+0x910,16,'physical-mmio-result'))
            if dte_base != base+reserved or transaction:
                raise ValueError('Board MMIO test must be skipped on the virtual platform')
            queues = memory(dte_base+0x204000,8192,'physical-mmio-empty-queues')
            if any(queues):
                raise ValueError('Reserved command or event queue was changed in QEMU')
            result['PhysicalMmioExcluded']=True
        if detached:
            first_iova = 0x08000000
            if radix != first_iova+used or dma_root != base+payload_pages*4096:
                raise ValueError('Detached GSP directory or DMA root is misplaced')
            middle, leaves = radix+4096, radix+8192
            directory = bytearray(directory_pages*4096)
            struct.pack_into('<Q',directory,0,middle)
            for index in range(directory_pages-2):
                struct.pack_into('<Q',directory,4096+index*8,leaves+index*4096)
            for index in range(image_pages):
                struct.pack_into('<Q',directory,8192+index*8,first_iova+index*4096)
            directory_end = payload_pages*4096
            if image[used:directory_end]!=directory:
                raise ValueError('Radix3 does not map each signed firmware page exactly once')

            tree = bytearray(tree_pages*4096)
            read = 1<<61
            for index in range(tree_pages-1):
                struct.pack_into('<Q',tree,((first_iova>>21)+index)*8,
                                 (dma_root+(index+1)*4096)|read|0x201)
            for index in range(payload_pages):
                struct.pack_into('<Q',tree,4096+index*8,(base+index*4096)|read|1)
            used = directory_end+len(tree)
            if queues:
                if rmargs != queue_iova or first_iova+directory_end>queue_iova:
                    raise ValueError('GSP queue IOVA overlaps firmware or moved')
                page_table = base+used+queue_bytes+libos_bytes
                write = 1<<62
                struct.pack_into('<Q',tree,(queue_iova>>21)*8,page_table|read|write|0x201)
            if image[directory_end:used]!=tree:
                raise ValueError('Unexpected mapping or permission in the detached GSP DMA tree')
            result.update(GspDetachedDmaVerified=True,GspRadix3Pages=directory_pages,
                          GspReadOnlyDmaPages=payload_pages,GspDmaTablePages=tree_pages,
                          GspRadix3SHA256=hashlib.sha256(directory).hexdigest())
        if queues:
            args = encode(rmargs,[rmargs+4096*index for index in range(1,queue_pages)])
            if image[used:used+queue_bytes]!=args:
                raise ValueError('Ring 0 RMARGS, GspMem or initial MSGQ bytes differ from HOST')
            table = bytearray(4096)
            for index in range(queue_pages):
                permissions = read | (write if index>=2 else 0)
                struct.pack_into('<Q',table,index*8,(base+used+index*4096)|permissions|1)
            used += queue_bytes
            if libos:
                if libos_iova != rmargs+queue_bytes:
                    raise ValueError('LIBOS arguments are outside the reserved IOVA layout')
                libos_image = encode_libos(libos_iova, rmargs)
                if image[used:used+libos_bytes]!=libos_image:
                    raise ValueError('LIBOS descriptors, log pointers or zero padding differ from HOST')
                for index in range(LIBOS_PAGES):
                    permissions = read | (write if index else 0)
                    struct.pack_into('<Q',table,(queue_pages+index)*8,(base+used+index*4096)|permissions|1)
                used += libos_bytes
                result.update(GspLibosVerified=True,GspLibosPages=LIBOS_PAGES,
                              GspLibosSHA256=hashlib.sha256(libos_image).hexdigest())
            if boot_chain:
                if boot_iova!=rmargs+queue_bytes+libos_bytes:
                    raise ValueError('Signed boot chain IOVA is outside its expected aperture')
                first = (boot_iova-rmargs)//4096
                for index in range(boot_chain['pages']):
                    struct.pack_into('<Q',table,(first+index)*8,(base+used+4096*(1+index))|read|1)
            if image[used:used+4096]!=table:
                raise ValueError('Detached GSP queue permissions differ')
            used += 4096
            result.update(GspQueuePagesVerified=queue_pages,GspQueuePermissionsVerified=True,
                          GspQueueReadOnlyPages=2,GspQueueWritablePages=queue_pages-2,
                          GspQueueSHA256=hashlib.sha256(args).hexdigest())
        if boot_chain:
            chain = image[used:used+boot_chain['pages']*4096]
            if hashlib.sha256(chain).hexdigest()!=boot_chain['sha256']:
                raise ValueError('Ring 0 signed boot chain differs from HOST')
            for role,entry in boot_chain['entries'].items():
                start,end = entry['offset'],entry['offset']+entry['bytes']
                if hashlib.sha256(chain[start:end]).hexdigest()!=entry['sha256'] or any(chain[end:(end+4095)&-4096]):
                    raise ValueError(f'Signed payload or padding differs: {role}')
            used += len(chain)
            result.update(GspBootChainVerified=True,GspBootChainPages=boot_chain['pages'],
                          GspBootChainSHA256=boot_chain['sha256'])
        if wpr_page:
            if wpr_iova or any(image[used:used+4096]):
                raise ValueError('Standard VGA must leave the WPR page zeroed and unpublished')
            used += 4096
            result['GspWprPageExcluded']=True
        if fwsec:
            end = used+fwsec['pages']*4096
            if fuse or fwsec_iova or any(image[used:end]):
                raise ValueError('Standard VGA must erase the FWSEC payload and leave its IOVA unpublished')
            used = end
            result['GspFwsecExcluded']=True
        if any(image[used:]):
            raise ValueError('GSP reservation lost its zero padding')
        return result
    if (prepared or firmware or signature or
            hashlib.sha256(image[:length]).hexdigest()!=expected['sha256'] or any(image[length:])):
        raise ValueError('GSP resident bytes or final page padding differ')
    return dict(GspResidentVerified=True,GspResidentBytes=length,GspReservedPages=reserved//4096)

def verify_storage_state(machine, pci_tree, memory, context, serial, *, quiesce=None):
    ahci, nvme = 0x010601, 0x010802
    read = lambda address: int(machine.command('readl',address),16)
    selector = int(machine.command('inl',0xcf8),16)
    actual = {}
    try:
        for rid,entry in pci_tree.items():
            kind = machine.pci(8,requester=rid)>>8
            if kind not in (ahci,nvme):
                continue
            region, = (bar for bar in entry['regions'] if bar['bar']==(5 if kind==ahci else 0))
            bar, length = region['address'],region['size']
            command = machine.pci(4,word=True,requester=rid)
            if not command&2:
                raise ValueError(f'Storage decode disabled in QEMU for {rid:04X}')
            a,b = (read(bar+4),read(bar+12)) if kind==ahci else (read(bar+0x14),read(bar+0x1c))
            engines = pending = 0
            if kind==ahci and a>>31:
                for port in range(32):
                    if b & 1<<port:
                        offset=bar+0x100+port*0x80
                        engines |= bool(read(offset+0x18)&0xc011)<<port
                        pending |= bool(read(offset+0x34)|read(offset+0x38))<<port
            actual[rid]=(kind,bar,length,machine.pci(0,requester=rid),command,2,a,b,engines,pending)
    finally:
        machine.command('outl',0xcf8,selector)
    if sorted(row[0] for row in actual.values())!=[ahci,nvme]:
        raise ValueError('QEMU must expose one AHCI and one NVMe controller')
    stored,total=struct.unpack('<2I',memory(context+0xb50,8,'storage-state-count'))
    if (stored,total)!=(2,2):
        raise ValueError(f'Storage handoff count {stored}/{total}')
    rows=list(struct.iter_unpack('<HHIQQIHHIIII',memory(context+0xf90,96,'storage-state-rows')))
    observed={rid:tuple(tail) for rid,_,*tail in rows}
    proof={}
    if quiesce is not None:
        from storage_quiesce_capture import verify_storage_quiesce
        proof=verify_storage_quiesce(memory,context,rows,actual,quiesce)
    if not quiesce and observed!=actual:
        raise ValueError(f'Storage handoff {observed} differs from QEMU {actual}')
    lines=[line for line in serial.read_text(errors='replace').splitlines()
           if line.startswith(('STORAGE_COUNT=','STORAGE_ROW='))]
    expected=['STORAGE_COUNT=00000002 00000002']
    expected += [f'STORAGE_ROW={rid:04X} {kind:06X} {pre:04X} {post:04X} {status} '
                 f'{a:08X} {b:08X} {engines:08X} {pending:08X}'
                 for rid,pre,kind,_,_,_,post,status,a,b,engines,pending in rows]
    if lines!=expected:
        raise ValueError('Ring 3 storage report differs from the kernel snapshot')
    return dict(StorageStateVerified=True,StorageStateReport=lines,**proof)


def verify_dma_census(machine, command, memory, context, serial, *, storage_state=False, quiesce=None):
    def functions(devices):
        for entry in devices:
            yield (entry['bus'] << 8 | entry['slot'] << 3 | entry['function']), entry
            yield from functions(entry.get('pci_bridge', {}).get('devices', []))

    pci_tree = dict(functions(device for bus in command('query-pci') for device in bus['devices']))
    owner, = (rid for rid, entry in pci_tree.items() if entry['qdev_id'] == 'bmo-native-xhci')
    expected = []
    selector = int(machine.command('inl', 0xcf8), 16)
    try:
        for rid in sorted(pci_tree):
            pci_command = machine.pci(4, word=True, requester=rid)
            if pci_command & 4:
                ids = machine.pci(0, requester=rid)
                kind = machine.pci(8, requester=rid) >> 8
                expected.append((rid, pci_command, ids, kind))
    finally:
        machine.command('outl', 0xcf8, selector)
    if owner < 256 or not any(row[0] == owner and row[3] == 0x0c0330 for row in expected):
        raise ValueError('Expected a bus-mastering xHCI behind a PCIe bridge')
    header, ready = struct.unpack('<QB', memory(context+0xb80, 9, 'dma-census-header'))
    stored, xhci, total = header & 0xffff, (header >> 16) & 0xffff, header >> 32
    if (ready, stored, xhci, total) != (1, min(len(expected), 64), owner, len(expected)):
        raise ValueError(f'PCI DMA inventory {stored}/{total}, xHCI {xhci:04X}, differs from {expected}')
    rows = list(struct.iter_unpack('<HHIQ', memory(context+0xb90, stored*16, 'dma-census-rows')))
    lines = [line for line in serial.read_text(errors='replace').splitlines()
             if line.startswith(('DMA_CENSUS=', 'DMA_REQ='))]
    expected_lines = [f'DMA_CENSUS={total:08X} {owner:04X} {stored:04X}']
    expected_lines += [f'DMA_REQ={rid:04X} {ctrl:04X} {ids:08X} {kind:06X}' for rid, ctrl, ids, kind in rows]
    if rows != expected[:64] or lines != expected_lines:
        raise ValueError('PCI DMA inventory differs from PCI configuration or the Ring 3 report')
    proof=dict(DmaCensusVerified=True, DmaCensusActive=total, DmaCensusXhci=f'{owner:04X}', DmaCensusReport=lines)
    if storage_state:
        proof.update(verify_storage_state(machine,pci_tree,memory,context,serial,quiesce=quiesce))
    return proof


def verify_native_ui(command,memory,prefix,image,case,symbols_path,*,amdvi_coexist=None,dma_census=None,
                     amdvi_dte_reserve=False):
    if case=='external-permissions':
        result=verify_external_rejection(command,memory,image)
        if memory(0x4000000,4096,'ui-rejected-code')!=bytes(4096):raise ValueError('UI copied before permission validation')
        return result
    symbols=json.loads(symbols_path.read_text())
    run=prefix.parent.parent
    empty_usb=(run/'native-usb-empty.txt').is_file()
    gop_regions=(run/'gop-regions.txt').is_file()
    storage_lab=(run/'storage-quiesce.txt').is_file()
    metal_quiesce=(run/'storage-quiesce-metal.txt').is_file()
    full_hd_profile=bool(symbols.get('full_hd'))
    uses_full_hd=full_hd_profile and case=='normal'
    render_width,render_height=(1920,1080) if uses_full_hd else (1280,800)
    start_x,start_y=(960,600) if uses_full_hd else (640,400)
    surface_bytes=render_width*render_height*4
    data_end=0x41000000 if full_hd_profile else 0x40e00000
    state,pixels=symbols['state'],symbols['pixels']
    if not (0x40400000<=state<=data_end-64 and 0x40400000<=pixels<=data_end-surface_bytes):
        raise ValueError('UI symbol range')
    serial=Path(str(prefix)+'-serial.log')
    def regs():return command('human-monitor-command',{'command-line':'info registers'})
    observed=False
    def observe_ring3():
        nonlocal observed
        if not observed:
            r=regs()
            observed='CPL=3' in r and 0x40000000<=register(r,'RIP')<0x40200000
    # Software float rasterization under TCG can exceed 45 s. Both the
    # phase and DIRECTOR snapshots are published after frame presentation.
    frame_timeout=90
    def until(phase,accepted=0):
        deadline=time.monotonic()+frame_timeout
        while time.monotonic()<deadline:
            log=serial.read_text(errors='replace') if serial.exists() else ''
            if 'BMO UI FAIL:' in log:raise ValueError(log[-1800:]+'\n'+regs()[:600])
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'ui-state'))
            if words[0]==0x3149554f4d42 and words[1]==phase and words[4]>=accepted:return words
            if symbols.get('desktop'):observe_ring3()
            time.sleep(.07)
        raise ValueError('Native UI phase '+str(phase)+' not reached: '+str(words)+' '+log[-1400:]+'\n'+regs()[:600])
    def freeze_frame(phase,accepted=0):
        for _ in range(4):
            until(phase,accepted)
            command('stop')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'ui-frozen-state'))
            if words[1]==phase and words[4]>=accepted:return words
            command('cont')
        raise ValueError('Could not pause a completed native frame')
    first=freeze_frame(2)
    if not (first[2]>=1 and first[5]>0 and 0<first[6]<=first[7]<=4*1024*1024):raise ValueError('Invalid UI resource counters')
    raw=memory(pixels-0x3c000000,surface_bytes,'ui-frame')
    if symbols.get('usb')=='both' or (gop_regions and symbols.get('desktop')):
        for x,y,color in ((0,0,0x0b1019),(1,2,0xf4f8ff)):
            if struct.unpack_from('<I',raw,((start_y+y)*render_width+start_x+x)*4)[0]!=color:
                raise ValueError('Pointer missing before first input')
    registers=regs()
    if 'CPL=0' in registers:
        context_address=register(registers,'RBP')
    else:
        root=register(registers,'CR3')
        context_address=struct.unpack('<Q',memory(root+0x7320,8,'ui-handoff'))[0]
    if not 0x100000<=context_address<=0xffe0000:raise ValueError('Native UI handoff address')
    context=memory(context_address,0x30,'ui-context')
    if context[:8]!=b'METAL64!':raise ValueError('Native UI handoff signature')
    amdvi_proof={}
    gsp_path=run/'nvidia-gsp-stage.json'
    if gsp_path.is_file():
        gsp_manifest=json.loads(gsp_path.read_text(encoding='ascii'))
        amdvi_proof.update(verify_gsp_reservation(memory,context_address,gsp_manifest,case))
        if gsp_manifest.get('detached_dma'):
            ready = 5 if gsp_manifest.get('libos') else 4 if gsp_manifest.get('queues') else 3
            marker='GSP_PREP=1 0' if case=='amdvi-missing' else f'GSP_PREP=5 {ready}'
            if marker not in serial.read_text(errors='replace').splitlines():
                raise ValueError('Missing Ring 3 GSP status')
            amdvi_proof['GspStatusExportVerified']=True
    if full_hd_profile:
        pool,pages=struct.unpack('<QQ',memory(context_address+0x708,16,'native-ui-pool'))
        if (pool,pages)!=(0x04000000,4608):
            raise ValueError('Wrong Full HD private UI reservation')
        dimensions=struct.unpack_from('<II',context,32)
        selected=dimensions==(1920,1080)
        if selected!=uses_full_hd or f'GOP_FULL_HD={int(selected)}' not in serial.read_text(errors='replace').splitlines():
            raise ValueError(f'Full HD selection or fallback mismatch for {dimensions}')
        if not selected:
            amdvi_proof['FullHdFallbackVerified']=True
    if bool(symbols.get('dma_census')) != (dma_census is not None):
        raise ValueError('PCI DMA inventory profiles differ')
    if dma_census is not None:
        amdvi_proof.update(verify_dma_census(dma_census,command,memory,context_address,serial,
                                            storage_state=symbols.get('storage_state',False),
                                            quiesce=(case=='normal') if storage_lab else False if metal_quiesce else None))
    if symbols.get('amdvi_post'):
        base, _, _, status, control, table, cmd, events, hw_status, pte0, pte2 = struct.unpack(
            '<QII8Q', memory(context_address+0xb00,0x50,'amdvi-post'))
        expected = ('AMDVI_POST=01' if case == 'amdvi-missing' else
                    'AMDVI_POST=04 ' + ' '.join(f'{word:016X}' for word in (control,table,cmd,events,hw_status)))
        lines = serial.read_text(errors='replace').splitlines()
        if symbols.get('amdvi_mmio_report'):
            if status >> 32 or 'AMDVI_MMIO_TEST=000' not in lines:
                raise ValueError('Ring 3 must report the board-only register test as skipped in QEMU')
            amdvi_proof['PhysicalMmioReportVerified'] = True
        if expected not in lines:
            raise ValueError('Ring 3 AMD-Vi report differs from the Ring 0 snapshot')
        if case == 'amdvi-missing':
            if (base,status,control,table,cmd,events,hw_status,pte0,pte2) != (0,1,0,0,0,0,0,0,0):
                raise ValueError('Absent AMD-Vi opened a post-EBS alias')
            if amdvi_dte_reserve and memory(context_address+0x758,32,'dte-post-empty')!=bytes(32):
                raise ValueError('Absent AMD-Vi left DTE proof data behind')
            return dict(Case=case,Passed=True,AmdViPostVerified=True,AmdViPostReport='01',AmdViPostPages=0,**amdvi_proof)
        if base!=0xfed80000 or status!=4 or (pte0,pte2)!=(0x80000000fed80019,0x80000000fed82019):
            raise ValueError('Unexpected post-EBS AMD-Vi aperture or permissions')
        amdvi_proof.update(AmdViPostVerified=True,AmdViPostReport=expected.removeprefix('AMDVI_POST='),
                           AmdViPostPages=2,AmdViPostPtes=[f'{pte0:016X}',f'{pte2:016X}'])
        if amdvi_dte_reserve:
            dte_status,zero_qwords,first_pte,last_pte=struct.unpack(
                '<QQQQ',memory(context_address+0x758,32,'dte-post-proof'))
            reserve_base,reserve_pages,reserve_status,reserve_zero=struct.unpack(
                '<QQQQ',memory(context_address+0x738,32,'dte-reservation'))
            expected_first=reserve_base|0x8000000000000001
            expected_last=(reserve_base+511*4096)|0x8000000000000001
            expected_line=(f'AMDVI_DTE_POST=01 {zero_qwords:08X}')
            serial_lines=serial.read_bytes().splitlines()
            if (dte_status,zero_qwords)!=(1,262144) or reserve_status!=1 or reserve_pages!=512 or \
                    reserve_zero!=262144 or not reserve_base or reserve_base&0xfff or \
                    (first_pte,last_pte)!=(expected_first,expected_last) or \
                    expected_line.encode('ascii') not in serial_lines:
                raise ValueError('Post-EBS DTE read, read-only PTEs, or revocation did not verify')
            amdvi_proof.update(AmdViDtePostReadVerified=True,AmdViDtePostStatus=dte_status,
                               AmdViDtePostZeroQwords=zero_qwords,AmdViDtePages=reserve_pages,
                               AmdViDteBase=reserve_base,DteAliasReadOnly=True,DteAliasNx=True,
                               DteAliasRevoked=True,DtePostPtes=[f'{first_pte:016X}',f'{last_pte:016X}'])
    if symbols.get('usb')=='both':
        live=memory(context_address+0x1a3c8,1,'dual-live')[0]
        roles=memory(context_address+0x1a770,1,'dual-roles')[0]
        if empty_usb:
            halt=memory(context_address+0x1a37a,1,'empty-usb-halted')[0]
            pci=struct.unpack('<H',memory(context_address+0x1a37e,2,'empty-usb-pci'))[0]
            if live or roles or halt!=1 or pci&4 or memory(context_address+0x1e000,24,'empty-usb-aliases')!=bytes(24):
                raise ValueError('Empty USB startup did not revoke controller ownership')
        elif live!=1 or roles!=3:
            phase=struct.unpack('<I',memory(context_address+0x1a7ac,4,'dual-phase'))[0]
            cc=memory(context_address+0x1a7a0,1,'dual-cc')[0]
            debug=memory(context_address+0x1a000,4096,'dual-debug-state')
            memory(context_address+0x1e000,4096,'dual-debug-aliases')
            pointers=struct.unpack_from('<3Q',debug,0x740)
            reset=debug[0x3b9]
            dma=struct.unpack_from('<Q',debug,0x758)[0]
            if 0x100000<=dma<=0x10000000-14*4096:memory(dma,14*4096,'dual-debug-dma')
            raise ValueError(f'Dual USB init incomplete: live={live} roles={roles} phase={phase} CC={cc} reset={reset} regs={pointers}')
    fb=struct.unpack_from('<Q',context,16)[0]
    width,height,pitch,order=struct.unpack_from('<IIII',context,32)
    if not (640<=width<=4096 and 400<=height<=4096 and width<=pitch<=8192 and order in (0,1)):
        raise ValueError('Native UI framebuffer geometry')
    scale=min(width//render_width,height//render_height)
    dw,dh=(render_width*scale,render_height*scale) if scale else (640,400)
    x,y=(width-dw)//2,(height-dh)//2

    def position(index):
        return index*scale if scale else index//2

    def pixel_order(row):
        if order==1:
            return row
        converted=bytearray(row)
        converted[0::4],converted[2::4]=row[2::4],row[0::4]
        return converted

    displayed=memory(fb+(y*pitch+x)*4,((dh-1)*pitch+dw)*4,'ui-presented')
    for row in range(dh):
        sy=row//scale if scale else row*2
        expected=raw[sy*render_width*4:(sy+1)*render_width*4]
        if not scale:expected=b''.join(expected[i:i+4] for i in range(0,len(expected),8))
        expected=pixel_order(expected)
        if scale>1:expected=b''.join(expected[i:i+4]*scale for i in range(0,len(expected),4))
        if displayed[row*pitch*4:row*pitch*4+len(expected)]!=expected:
            raise ValueError('Native UI presentation differs at row '+str(row))
    (Path(str(prefix)+'-ui-xrgb.bin')).write_bytes(raw)
    command('screendump',{'filename':str(prefix)+'-ui.ppm'})
    if amdvi_coexist is not None:
        from amdvi_xhci import verify_coexistence
        guest_dma=(run/'amdvi-guest-dma.txt').is_file()
        amdvi_proof.update(verify_coexistence(amdvi_coexist,command,memory,context_address,symbols,
                           guest_dma=guest_dma, storage=(run/'amdvi-storage.txt').is_file(),
                           routed=(run/'amdvi-routed.txt').is_file(), nvme=(run/'amdvi-nvme.txt').is_file(),
                           guest_nvme=(run/'amdvi-guest-nvme.txt').is_file(),
                           guest_ahci=(run/'amdvi-guest-ahci.txt').is_file(),
                           gsp_dma=(run/'amdvi-gsp-dma.txt').is_file()))
        if (run/'amdvi-guest-ahci.txt').is_file():
            command('screendump',{'filename':str(prefix)+'-storage-lab.png','format':'png'})
        if amdvi_proof.get('NvmeTranslatedReadsVerified'):
            return dict(Case=case,Passed=True,Evidence='QEMU',PresentedPixelsVerified=dw*dh,**amdvi_proof)
    command('cont')
    if empty_usb:
        return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
            UsbEmptyPortsRejected=True,UsbControllerStopped=True,UsbBusMasterRevoked=True,
            UsbMmioRevoked=True,UsbBothDevicesVerified=False,PhysicalUsbVerified=False,
            PresentedPixelsVerified=dw*dh,FrameSHA256=hashlib.sha256(raw).hexdigest())
    display_proof={}
    if uses_full_hd:
        # The previous scaler duplicated the second pixel of every three.
        # Check the title band, outside the independently drawn mouse cursor.
        title=raw[200*render_width*4:300*render_width*4]
        if not any(title[i+4:i+8]!=title[i+8:i+12] for i in range(0,len(title),12)):
            raise ValueError('Full HD title still has the previous scaled pixel pattern')
        display_proof=dict(FullHdGopVerified=True,FullHdNativeRasterVerified=True,
                           DesktopRasterWidth=render_width,DesktopRasterHeight=render_height)
    if symbols.get('usb')=='both' or (gop_regions and symbols.get('desktop')):
        cursor_counter=context_address+0x1a7e0
        start=struct.unpack('<Q',memory(cursor_counter,8,'cursor-copy-baseline'))[0]
        delta=25 if uses_full_hd else 24
        for step,target in ((delta,start_x+delta),(-delta,start_x)):
            command('input-send-event',{'events':[{'type':'rel','data':{'axis':'x','value':step}}]})
            deadline=time.monotonic()+30
            # The white pixel is sampled by both the full and half-scale paths.
            px=target+2
            py=start_y+4
            gx=x+position(px)
            gy=y+position(py)
            while time.monotonic()<deadline:
                pixel=struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'fast-pointer'))[0]
                if pixel==(0xf4f8ff if order==1 else 0xfff8f4):break
                time.sleep(.02)
            else:
                memory(fb+gy*pitch*4,pitch*4,'fast-pointer-row')
                memory(state-0x3c000000,64,'fast-pointer-timeout-state')
                raise ValueError(f'Pointer did not reach {target}')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'fast-pointer-state'))
            if words[2]!=first[2]:raise ValueError('Pointer movement triggered a full RmlUi render')
        copied=struct.unpack('<Q',memory(cursor_counter,8,'cursor-copy-total'))[0]-start
        if scale==1 and copied!=4*12*17:raise ValueError('Wrong GOP cursor-region pixel count')
        if scale!=1 and copied:raise ValueError('Cursor region accepted an unsupported scale')
        if scale==1:
            old_x,old_y=start_x+delta,start_y
            for row in range(position(old_y),position(old_y+17)):
                span=(position(old_x+12)-position(old_x))*4
                actual=memory(fb+((y+row)*pitch+x+position(old_x))*4,span,'cursor-background')
                offset=(row*render_width+old_x)*4
                expected=pixel_order(raw[offset:offset+48])
                if actual!=expected:raise ValueError('Old cursor box did not restore the background')
        display_proof.update(PointerBeforeInputVerified=True,PointerMoveWithoutRasterVerified=True,
                             PointerRegionPixelsForTwoMoves=copied)
        if gop_regions and not symbols.get('usb'):
            if memory(context_address+0xb8,16,'native-no-usb-dma')!=bytes(16):
                raise ValueError('GOP-only profile reserved USB DMA')
            display_proof['GopRegionsWithoutXhciVerified']=scale==1
    if storage_lab:
        address=symbols['usb_keyboard_reports']-0x3c000000
        def keyboard_reports():
            return struct.unpack('<Q',memory(address,8,'storage-lab-keyboard'))[0]
        before=keyboard_reports()
        command('send-key',{'keys':[{'type':'qcode','data':'num_lock'}],'hold-time':110})
        deadline=time.monotonic()+20
        while keyboard_reports()<before+2:
            if time.monotonic()>=deadline:
                raise ValueError('USB keyboard stopped delivering reports after storage shutdown')
            time.sleep(.05)
        mouse_address=symbols['usb_mouse_reports']-0x3c000000
        mouse=struct.unpack('<Q',memory(mouse_address,8,'storage-lab-mouse'))[0]
        if mouse<2 or not display_proof.get('PointerMoveWithoutRasterVerified'):
            raise ValueError('USB mouse stopped delivering reports after storage shutdown')
        return dict(Case=case,Passed=True,Evidence='QEMU',StorageQuiesceHidVerified=True,
                    PresentedPixelsVerified=dw*dh,**amdvi_proof,**display_proof)
    before=hashlib.sha256(raw).hexdigest()
    command('send-key',{'keys':[{'type':'qcode','data':'ret'}],'hold-time':60})
    after=freeze_frame(3)
    if after[3:5]!=(1,1):raise ValueError('Native ULTRA-J action did not execute once')
    raw_after=memory(pixels-0x3c000000,surface_bytes,'ui-action-frame')
    if hashlib.sha256(raw_after).hexdigest()==before:raise ValueError('Native action did not change the rendered frame')
    command('screendump',{'filename':str(prefix)+'-ui-action.ppm'})
    command('cont')
    if symbols.get('desktop'):
        def mouse_event(event_type, **data):
            command('input-send-event',{'events':[{'type':event_type,'data':data}]})
        def wait_input(check, message, timeout=10):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if check():return
                time.sleep(.02)
            raise ValueError(message)
        target_y=790 if uses_full_hd else 527
        # USB boot mouse reports carry signed 8-bit deltas.
        while target_y-start_y>127:
            mouse_event('rel',axis='y',value=127)
            start_y+=127
            time.sleep(.12)
        mouse_event('rel',axis='y',value=target_y-start_y)
        mouse_edges=symbols.get('mouse_edges')
        if mouse_edges:
            px,py=start_x+2,target_y+4
            gx=x+position(px)
            gy=y+position(py)
            hover_color=0xa2f4e6 if order==1 else 0xe6f4a2
            wait_input(lambda: struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'button-hover'))[0]==hover_color,
                'Cursor did not highlight over Activate')
            words=struct.unpack('<8Q',memory(state-0x3c000000,64,'hover-frame-state'))
            if words[2]!=after[2]:raise ValueError('Button hover rasterized the desktop')
            def edges():
                return struct.unpack('<4Q',memory(mouse_edges-0x3c000000,32,'mouse-edges'))
            for index,name in ((1,'right'),(2,'middle'),(3,'wheel-up')):
                initial=edges()[index]
                mouse_event('btn',button=name,down=True)
                wait_input(lambda: edges()[index]==initial+1,'Missing '+name+' event')
                mouse_event('btn',button=name,down=False)
                if index!=3:
                    wait_input(lambda: edges()[index]==initial+2,'Missing '+name+' release')
        else:
            time.sleep(.2)
        mouse_event('btn',button='left',down=True)
        time.sleep(.2)
        mouse_event('btn',button='left',down=False)
        after=until(3,accepted=2)
        if after[3:5]!=(2,2):raise ValueError('Desktop mouse activation did not execute once')
        director=symbols['director']
        if not 0x40400000<=director<=0x40e00000-8:raise ValueError('DIRECTOR symbol')
        def policy(expected):
            deadline=time.monotonic()+(frame_timeout if uses_full_hd else 40)
            while time.monotonic()<deadline:
                observe_ring3()
                state=struct.unpack('<Q',memory(director-0x3c000000,8,'director-state'))[0]
                if state==expected:return
                time.sleep(.03)
            raise ValueError(f'DIRECTOR did not reach {expected:#x} after {last_keys}; last state {state:#x}')
        last_keys=()
        def key(*keys):
            nonlocal last_keys
            last_keys=keys
            if not uses_full_hd or symbols.get('usb')!='both' or keys==('f12',):
                command('send-key',{'keys':[{'type':'qcode','data':k} for k in keys],'hold-time':80})
                return
            # A full CPU render under TCG can delay HID polling. Have Ring 3
            # acknowledge each edge before pressing or releasing another key.
            keyboard_address=symbols['usb_keyboard_reports']-0x3c000000
            def reports():
                observe_ring3()
                return struct.unpack('<Q',memory(keyboard_address,8,'keyboard-edge-count'))[0]
            for down,sequence in ((True,keys),(False,reversed(keys))):
                for name in sequence:
                    before=reports()
                    command('input-send-event',{'events':[{'type':'key','data':{
                        'key':{'type':'qcode','data':name},'down':down}}]})
                    wait_input(lambda: reports()>before, f'Missing USB edge for {name} down={down}', 75)
        policy(0x101)
        focus_address=symbols.get('keyboard_focus')
        if focus_address:
            if not 0x40400000<=focus_address<=0x40e00000-8:raise ValueError('Keyboard focus symbol')
            def focus_count():
                return struct.unpack('<Q',memory(focus_address-0x3c000000,8,'keyboard-focus'))[0]
            initial_focus=focus_count()
            key('meta_l','1')
            wait_input(lambda: focus_count()==initial_focus+1,'Super+1 did not focus the RmlUi window')
        key('ctrl','meta_l','2');policy(2)
        key(*(['meta_l','spc'] if focus_address else ['f1']));policy(0x102)
        key('meta_l','q');policy(2)
        key('f1');policy(0x102)
        key('ctrl','meta_l','1');policy(1)
        key('ctrl','meta_l','2');policy(0x102)
        msvc_result={}
        if symbols.get('msvc_panel_draws'):
            address=symbols['msvc_panel_draws']
            if not 0x40400000<=address<=0x40e00000-8:raise ValueError('MSVC draw symbol')
            key('f3');policy(0x202)
            draws=struct.unpack('<Q',memory(address-0x3c000000,8,'msvc-draws'))[0]
            if draws<1:raise ValueError('MSVC client did not execute')
            msvc_frame=memory(pixels-0x3c000000,1280*800*4,'msvc-desktop-frame')
            if msvc_frame.count(bytes.fromhex('d5e77e00'))<9:raise ValueError('MSVC triangle missing')
            shot=Path(str(prefix)+'-msvc-rmlui.png')
            command('screendump',{'filename':str(shot),'format':'png'})
            key('meta_l','q');policy(0x102)
            for i in range(5):
                events=[{'type':'rel','data':{'axis':'x','value':-106}}]
                if i<2:
                    events.append({'type':'rel','data':{'axis':'y','value':-113}})
                command('input-send-event',{'events':events})
                time.sleep(.12)
            gx=x+position(112)
            gy=y+position(305)
            hover_color=0xa2f4e6 if order==1 else 0xe6f4a2
            wait_input(lambda: struct.unpack('<I',memory(fb+(gy*pitch+gx)*4,4,'msvc-launcher-pointer'))[0]==hover_color,
                       'Pointer did not reach the MSVC launcher')
            mouse_event('btn',button='left',down=True)
            time.sleep(.15)
            mouse_event('btn',button='left',down=False)
            policy(0x202)
            key('meta_l','q');policy(0x102)
            msvc_result=dict(MsvcPanelInRmlUiVerified=True,MsvcPanelCloseVerified=True,
                             MsvcMouseLauncherVerified=True,
                             MsvcPanelDraws=draws,MsvcScreenshot=shot.name,
                             MsvcScreenshotSHA256=hashlib.sha256(shot.read_bytes()).hexdigest())
        locks_verified=False
        lock_strip_verified=False
        if symbols.get('usb')=='both' and symbols.get('keyboard_leds'):
            def led_state():
                data=memory(context_address+0x1a7f0,16,'usb-keyboard-led')
                return struct.unpack_from('<Q',data)[0],data[9],data[10],data[11]
            wait_input(lambda: led_state()==(1,0,0,0),'Initial keyboard LED report failed')
            frame_count=struct.unpack('<Q',memory(state-0x3c000000+16,8,'lock-frame-count'))[0]
            region_counter=context_address+0x1a7e0
            def region_pixels():
                return struct.unpack('<Q',memory(region_counter,8,'lock-region-count'))[0]
            pixels_before=region_pixels()
            for count,(lock,mask) in enumerate(
                (('num_lock',1),('caps_lock',3),('scroll_lock',7),('caps_lock',5),
                 ('scroll_lock',1),('num_lock',0)),2):
                key(lock)
                wait_input(lambda: led_state()==(count,0,0,mask),'Keyboard LED report failed for '+lock,45)
            locks_verified=True
            frames_after=struct.unpack('<Q',memory(state-0x3c000000+16,8,'lock-frame-count'))[0]
            if frames_after!=frame_count:raise ValueError('Lock keys rendered the full desktop')
            status_rows=120 if uses_full_hd else 80
            if scale==1 and region_pixels()-pixels_before!=6*render_width*status_rows:
                raise ValueError('Lock indicators copied outside the GOP status strip')
            lock_strip_verified=True
        if not observed:raise ValueError('No DIRECTOR/RmlUi execution observed in CPL3')
        command('screendump',{'filename':str(prefix)+'-desktop.ppm'})
        usb_proof={}
        if symbols.get('usb'):
            address=symbols['usb_reports']
            if not 0x40400000<=address<=0x40e00000-8:raise ValueError('USB counter symbol')
            count=struct.unpack('<Q',memory(address-0x3c000000,8,'native-usb-reports'))[0]
            if count<3:raise ValueError('Missing actual USB reports in native UI')
            status=memory(context_address+0x1a3c4,5,'native-usb-owner')
            if status[0]!=1 or status[4]!=1:raise ValueError('USB DMA validation or live ownership missing')
            dma,pages=struct.unpack('<QQ',memory(context_address+0xb8,16,'native-usb-reservation'))
            expected_pages=14 if symbols['usb']=='both' else 10
            if pages!=expected_pages or dma<0x100000 or dma+pages*4096>0x10000000:
                raise ValueError('USB reservation outside the private identity map')
            for index in range(dma//0x200000,(dma+pages*4096-1)//0x200000+1):
                entry=struct.unpack('<Q',memory(context_address+0x15000+index*8,8,'usb-dma-pde'))[0]
                if entry&0x85!=0x81 or entry&0x000fffffffe00000!=index*0x200000:
                    raise ValueError('USB DMA mapping is not supervisor identity memory')
            aliases=struct.unpack('<3Q',memory(context_address+0x1e000,24,'usb-mmio-aliases'))
            if any(entry&5!=1 or not entry>>63 for entry in aliases):
                raise ValueError('USB MMIO alias must remain supervisor NX')
            usb_proof=dict(UsbProfile=symbols['usb'],UsbInputVerified=True,UsbReportCount=count,
                UsbRing3Decoder=True,UsbDmaSupervisorOnly=True,UsbPs2FallbackDisabled=True,
                UsbDmaReservedBytes=pages*4096,UsbMmioSupervisorNxVerified=True,
                UsbTransportBackend='Existing single-device QEMU diagnostic; mediated by Ring0',
                PhysicalUsbVerified=False)
            if symbols['usb']=='both':
                keyboard=struct.unpack('<Q',memory(symbols['usb_keyboard_reports']-0x3c000000,8,'dual-keyboard-count'))[0]
                mouse=struct.unpack('<Q',memory(symbols['usb_mouse_reports']-0x3c000000,8,'dual-mouse-count'))[0]
                slots=memory(dma+0x9800,128,'dual-slot-owners')
                if keyboard<2 or mouse<3 or {slots[3],slots[67]}!={1,2} or slots[14]!=1 or slots[78]!=1 or slots[1]==slots[65]:
                    raise ValueError('Two distinct active USB devices not proven')
                code,code_pages=struct.unpack('<QQ',memory(context_address+0x728,16,'dual-code-reservation'))
                if code_pages!=2 or code&4095 or code<0x100000 or code+8192>0x10000000:
                    raise ValueError('Dual code reservation')
                stage=(prefix.parent.parent/'xhci.bin').read_bytes()
                if memory(code,8192,'dual-code-copy')!=stage.ljust(8192,b'\0'):raise ValueError('Dual code copy')
                if dma_census is not None:
                    def frame_counter():
                        return struct.unpack('<2Q',memory(state-0x3c000000+8,16,'dma-panel-frame'))
                    def toggle_panel(status):
                        _, previous=frame_counter()
                        key('f2')
                        def presented():
                            contents=serial.read_text(errors='replace')
                            if 'BMO UI FAIL:' in contents:raise ValueError(contents[-1800:])
                            phase, frames=frame_counter()
                            return f'DMA_PANEL={status}' in contents and phase==3 and frames>previous
                        wait_input(presented, 'DMA inventory panel did not switch to '+status, 75)
                    toggle_panel('ON')
                    shot=Path(str(prefix)+'-dma-census.ppm')
                    command('screendump',{'filename':str(shot)})
                    if symbols.get('storage_state'):
                        _, previous=frame_counter()
                        key('f3')
                        def storage_open():
                            phase, frames=frame_counter()
                            return 'STORAGE_PANEL=ON' in serial.read_text(errors='replace') and phase==3 and frames>previous
                        wait_input(storage_open, 'F3 did not present the storage handoff page', 75)
                        storage_shot=Path(str(prefix)+'-storage-state.ppm')
                        command('screendump',{'filename':str(storage_shot)})
                        amdvi_proof.update(StoragePanelVerified=True,StorageScreenshot=storage_shot.name,
                                           StorageScreenshotSHA256=hashlib.sha256(storage_shot.read_bytes()).hexdigest())
                    toggle_panel('OFF')
                    amdvi_proof.update(DmaCensusPanelVerified=True,DmaCensusScreenshot=shot.name,
                                       DmaCensusScreenshotSHA256=hashlib.sha256(shot.read_bytes()).hexdigest())
                if symbols.get('rtx_lab_panel'):
                    shot=Path(str(prefix)+'-rtx-lab.ppm')
                    for status in ('ON','OFF'):
                        _, previous=frame_counter()
                        key('f4')
                        def rtx_panel_presented():
                            phase, frames=frame_counter()
                            lines=serial.read_text(errors='replace').splitlines()
                            return f'RTX_LAB={status}' in lines and phase==3 and frames>previous
                        wait_input(rtx_panel_presented, 'F4 RTX panel did not switch to '+status, 75)
                        if status=='ON':
                            command('screendump',{'filename':str(shot)})
                    amdvi_proof.update(RtxLabPanelVerified=True,RtxLabScreenshot=shot.name)
                # Exercise the real application stop path, then require BM revoke
                # and alias removal. Buffers stay pinned, never silently reused.
                key('f12')
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    if memory(context_address+0x1a3c8,1,'dual-stopped')==b'\0':break
                    time.sleep(.03)
                else:raise ValueError('Dual controller did not stop')
                halt=memory(context_address+0x1a37a,1,'dual-halted')[0]
                pci=struct.unpack('<H',memory(context_address+0x1a37e,2,'dual-bus-master'))[0]
                if halt!=1 or pci&4 or memory(context_address+0x15400,8,'dual-alias-pde')!=bytes(8) or memory(context_address+0x1e000,24,'dual-alias-revoked')!=bytes(24):
                    raise ValueError('Dual stop/revocation incomplete')
                usb_proof.update(UsbBothDevicesVerified=True,UsbKeyboardReports=keyboard,UsbMouseReports=mouse,
                    MouseReportDescriptorDecoded=True, MouseButtonHoverWithoutRasterVerified=bool(mouse_edges),
                    KeyboardLedOutputReportsVerified=locks_verified,
                    LockIndicatorsWithoutFullRasterVerified=lock_strip_verified,
                    MouseRightMiddleWheelVerified=bool(mouse_edges),
                    UsbStopVerified=True,UsbBusMasterRevoked=True,UsbMmioRevoked=True,
                    UsbTransportBackend='Dynamic USB2 two-slot mediated transport',UsbCodePages=2)
        return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
            NativeUltraJAction=True,DirectorRust=True,WorkspaceSwitchVerified=True,
            SuperQVerified=True,SuperDigitFocusVerified=bool(focus_address),SuperSpaceLauncherVerified=bool(focus_address),
            ReopenVerified=True,KeyboardEnterVerified=True,MouseClickVerified=True,ShellRemainsAlive=True,
            HeapPeakBytes=after[7],HeapLimitBytes=4*1024*1024,FramebufferBytes=len(raw),SbefBytes=len(image),
            StagedModuleSHA256=hashlib.sha256(struct.pack('<Q',len(image))+image).hexdigest(),
            PresentedPixelsVerified=dw*dh,GopWidth=width,GopHeight=height,HalfScale=scale==0,
            FrameSHA256=before,**display_proof,**usb_proof,**msvc_result,**amdvi_proof)
    command('input-send-event',{'events':[{'type':'rel','data':{'axis':'y','value':127}}]})
    time.sleep(.2)
    command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':True}}]})
    time.sleep(.2)
    command('input-send-event',{'events':[{'type':'btn','data':{'button':'left','down':False}}]})
    pointer=until(3,accepted=2)
    if pointer[3:5]!=(2,2):raise ValueError('Mouse action was not delivered exactly once')
    command('screendump',{'filename':str(prefix)+'-ui-mouse.ppm'})
    command('send-key',{'keys':[{'type':'qcode','data':'esc'}],'hold-time':60})
    closed=until(4)
    final_regs=regs()
    if 'CPL=3' not in final_regs or not 0x40000000<=register(final_regs,'RIP')<0x40200000:
        raise ValueError('UI shutdown did not finish in CPL3: '+final_regs[:600])
    return dict(Case='normal',Passed=True,Evidence='QEMU',CPL=3,FullRmlUiEngine=True,
        RmlUi='6.3',FontEngine='FreeType 2.14.3',Renderer='Shared Rust CPU',NativeUltraJAction=True,
        MouseClickVerified=True,KeyboardEnterVerified=True,
        Frames=closed[2],Triangles=closed[5],HeapPeakBytes=closed[7],HeapLimitBytes=4*1024*1024,
        FramebufferBytes=len(raw),SbefBytes=len(image),ClosedResources=True,
        StagedModuleSHA256=hashlib.sha256(struct.pack('<Q',len(image))+image).hexdigest(),
        PresentedPixelsVerified=dw*dh,
        FrameSHA256=before,ActionFrameSHA256=hashlib.sha256(raw_after).hexdigest())
