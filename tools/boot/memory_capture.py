"""Check the physical frame selected in Ring 0 from the QEMU snapshot."""
from cpu_config import register


def memory_evidence(memory, snapshot, regions, context, code, reject, *, cycle=False):
    page = 4096
    marker = b'BFRAME0!'
    conventional = [(base, pages) for kind, base, _, pages, _ in regions if kind == 7 and pages]
    candidates = [base for base, _ in conventional
                  if 0x100000 <= base <= 0x10000000 - page and base % page == 0
                  and base != code and not context <= base < context + 0x20000]
    if not candidates:
        raise ValueError('MEMORY-QEMU: no hay marco convencional elegible')
    address = candidates[0]
    covering = [(kind, base) for kind, base, _, pages, _ in regions
                if pages and base < address + page and address < base + pages * page]
    if covering != [(7, address)] or register(snapshot, 'RSP') != context + 0x1fff8:
        raise ValueError('MEMORY-QEMU: solapamiento de marco o cambio de pila')
    actual = tuple(register(snapshot, name) for name in ('RDI', 'R11', 'R12'))
    data = memory(address, page if cycle else len(marker), 'frame-data' if cycle else 'frame-marker')
    extra = {}
    if cycle:
        owner, steps = (register(snapshot, name) for name in ('R13', 'R14'))
        if reject:
            if (owner, steps) != (0, 0):
                raise ValueError('FRAME-CYCLE-QEMU: contexto invalido cambio el estado del marco')
        elif (owner, steps) != (2, 0x3f) or data != bytes(page):
            raise ValueError('FRAME-CYCLE-QEMU: estado final o borrado del marco incorrecto')
        extra.update(FrameOwner=owner, FrameCycleMask=steps, ScrubbedBytes=0 if reject else page,
                     FrameCycleSteps=[] if reject else ['allocated', 'exhaustion-rejected', 'foreign-release-rejected',
                                                      'released', 'double-release-rejected', 'reallocated'])
    if reject:
        if actual != (0, 0, 0) or data[:len(marker)] == marker:
            raise ValueError('MEMORY-QEMU: entrega invalida aceptada')
    elif actual != (context, address, 1) or (not cycle and data != marker):
        raise ValueError('MEMORY-QEMU: direccion o marca fisica distinta')
    return dict(ContextAccepted=not reject, FrameTested=not reject,
                FrameAddress=None if reject else f'0x{address:X}',
                FrameBytes=0 if reject else page, MarkerBytes=0 if reject else page if cycle else len(marker),
                ConventionalBytes=sum(pages for _, pages in conventional) * page,
                MemoryMapEntries=len(regions), FaultInjection='RDI=0 al entregar' if reject else None, **extra)
