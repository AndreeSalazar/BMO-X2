"""Check the hardware fault, kernel stack switch and user page teardown."""
import re
import struct

from cpu_config import register


def user_fault_evidence(memory, snapshot, context, code, reject):
    base = context + 0x13000
    descriptors = base + 0x7000
    supplied, root, status, old, marker, cr3, rsp = (
        register(snapshot, name) for name in ('RDI', 'R11', 'R12', 'R13', 'R14', 'CR3', 'RSP'))
    if reject:
        if (supplied, root, status, marker, cr3, rsp) != (0, 0, 0, 0, old, context + 0x1fff8):
            raise ValueError('USER-FAULT-QEMU: entrega invalida cambio el contexto')
        return dict(ContextAccepted=False, UserFaultHandled=False, ReclaimedPages=0,
                    FaultInjection='RDI=0 al entregar', ActiveCR3=f'0x{cr3:X}')
    if (supplied, root, status, marker, cr3, rsp) != (
            context, base, 1, 0x2133524553554d42, base, descriptors + 4096 - 48):
        raise ValueError('USER-FAULT-QEMU: el manejador no termino en la pila de Ring 0')
    if cr3 == old or register(snapshot, 'CR2') != 0x100000 or register(snapshot, 'CS') != 8:
        raise ValueError('USER-FAULT-QEMU: CR3, CR2 o CS inesperado')
    if not register(snapshot, 'CR0') & 0x10000 or not register(snapshot, 'EFER') & 0x800:
        raise ValueError('USER-FAULT-QEMU: faltan WP o NXE')
    idtr = re.search(r'^IDT=\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', snapshot, re.M)
    tr = re.search(r'^TR\s*=\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', snapshot, re.M)
    if not idtr or tuple(int(value, 16) for value in idtr.groups()) != (descriptors + 0x200, 239):
        raise ValueError('USER-FAULT-QEMU: IDTR inesperado')
    if not tr or tuple(int(value, 16) for value in tr.groups()) != (40, descriptors + 0x100):
        raise ValueError('USER-FAULT-QEMU: TSS inesperada')

    page = memory(descriptors, 4096, 'user-fault-descriptors')
    handler = code + 536
    gate = struct.pack('<HHBBHII', handler & 0xffff, 8, 0, 0x8e,
                       (handler >> 16) & 0xffff, handler >> 32, 0)
    if page[0x200:0x2f0] != bytes(14 * 16) + gate:
        raise ValueError('USER-FAULT-QEMU: puerta 14 distinta')
    if struct.unpack_from('<Q', page, 0x104)[0] != descriptors + 4096:
        raise ValueError('USER-FAULT-QEMU: RSP0 de la TSS distinto')
    error, rip, cs, flags, user_rsp, ss = struct.unpack_from('<QQQQQQ', page, 4096 - 48)
    if (error, rip, cs, user_rsp, ss) != (5, 0x40000010, 0x23, 0x40001ff8, 0x1b) or flags & 0x3200:
        raise ValueError('USER-FAULT-QEMU: marco hardware de CPL3 distinto')

    tables = memory(base, 5 * 4096, 'user-fault-tables')
    expected = {0: (base + 0x1000) | 7, 512: (base + 0x2000) | 3,
                513: (base + 0x3000) | 7, 1536: (base + 0x4000) | 7}
    expected.update({1024 + index: (index << 21) | 0x83 for index in range(128)})
    for index, (entry,) in enumerate(struct.iter_unpack('<Q', tables)):
        wanted = expected.get(index, 0)
        if (entry & ~0x60 if wanted else entry) != wanted:
            raise ValueError(f'USER-FAULT-QEMU: entrada final {index} distinta')
    if memory(base + 0x5000, 8192, 'user-fault-erased-pages') != bytes(8192):
        raise ValueError('USER-FAULT-QEMU: codigo o pila de usuario conserva datos')
    return dict(ContextAccepted=True, UserCPL=cs & 3, UserFaultHandled=True,
                FaultVector=14, FaultErrorCode=error, FaultAddress='0x100000',
                SavedUserRIP=f'0x{rip:X}', SavedUserRSP=f'0x{user_rsp:X}',
                KernelFaultRSP=f'0x{rsp:X}', ActiveCR3=f'0x{cr3:X}',
                FrameBytes=32768, ReclaimedPages=2, ScrubbedBytes=8192)
