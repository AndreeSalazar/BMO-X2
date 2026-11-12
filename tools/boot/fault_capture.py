"""Validate the active IDTR, gate and CPU exception frame from QEMU."""
import re
import struct
from cpu_config import register


def fault_evidence(memory, snapshot, context, code, reject):
    old, new, supplied, status = (register(snapshot, n) for n in ('RSI','RSP','RDI','RAX'))
    base = context + 0x14000
    idt = re.search(r'^IDT=\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', snapshot, re.M)
    if not idt or old != context + 0x1fff8:
        raise ValueError('FAULT-QEMU: falta IDTR o pila de entrega')
    idtr = tuple(int(value,16) for value in idt.groups())
    page = memory(base, 4096, 'own-idt')
    if reject:
        if (supplied,status,new) != (0,0,old) or idtr[0] == base or any(page):
            raise ValueError('FAULT-QEMU: la entrega invalida altero IDT o pila')
        return dict(ContextAccepted=False, FaultHandled=False, FaultInjection='RDI=0 al entregar')
    if (supplied,status,new) != (context,6,base-40) or idtr != (base,111):
        raise ValueError('FAULT-QEMU: no se activo la IDT o la pila esperadas')
    cs = register(snapshot,'CS')
    handler = code+126
    gate = struct.pack('<HHBBHII',handler & 0xffff,cs,0,0x8e,(handler>>16)&0xffff,handler>>32,0)
    if page[:112] != bytes(96)+gate or page[256:266] != struct.pack('<HQ',111,base):
        raise ValueError('FAULT-QEMU: descriptor IDT distinto')
    rip, saved_cs, flags, saved_rsp, _ = struct.unpack('<QQQQQ',memory(new,40,'fault-frame'))
    if (rip,saved_cs,saved_rsp) != (code+122,cs,base) or flags & 0x200 or register(snapshot,'RDX') != rip:
        raise ValueError('FAULT-QEMU: marco o RIP de #UD distinto')
    return dict(ContextAccepted=True,FaultHandled=True,FaultVector=6,FaultRip=f'0x{rip:X}',
                FaultOffset=rip-code,IdtBase=f'0x{base:X}',IdtLimit=111,StackFrameBytes=40)
