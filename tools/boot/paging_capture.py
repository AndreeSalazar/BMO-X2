"""Verify the active x86-64 tables from the QEMU physical snapshot."""
import struct

from cpu_config import register


PAGE = 4096
FRAMES = 6
MARKER = b'BMPAGE0!'


def paging_evidence(memory, snapshot, regions, context, code, reject):
    def overlaps(start, end, other_start, other_end):
        return start < other_end and other_start < end

    length = FRAMES * PAGE
    candidates = [base for kind, base, _, pages, _ in regions
                  if kind == 7 and pages >= FRAMES and base % PAGE == 0
                  and 0x100000 <= base <= 0x10000000 - length
                  and not overlaps(base, base + length, code, code + PAGE)
                  and not overlaps(base, base + length, context, context + 0x20000)]
    if not candidates:
        raise ValueError('PAGING-QEMU: faltan seis marcos convencionales contiguos')
    base = candidates[0]
    covering = [(kind, start) for kind, start, _, pages, _ in regions
                if pages and overlaps(base, base + length, start, start + pages * PAGE)]
    if covering != [(7, base)] or register(snapshot, 'RSP') != context + 0x1fff8:
        raise ValueError('PAGING-QEMU: solapamiento o pila distinta')

    supplied, selected, status, old_cr3, cr3 = (
        register(snapshot, name) for name in ('RDI', 'R11', 'R12', 'R13', 'CR3'))
    data = memory(base + 5 * PAGE, PAGE, 'paging-data')
    if reject:
        if (supplied, selected, status, cr3) != (0, 0, 0, old_cr3) or data.startswith(MARKER):
            raise ValueError('PAGING-QEMU: contexto invalido altero CR3 o el marco de datos')
        return dict(ContextAccepted=False, PagingInstalled=False, FrameBytes=0,
                    FaultInjection='RDI=0 al entregar', ActiveCR3=f'0x{cr3:X}')

    if (supplied, selected, status, cr3) != (context, base, 1, base) or cr3 == old_cr3:
        raise ValueError('PAGING-QEMU: fallo la activacion o la lectura por el alias')
    cr0, cr4, efer = (register(snapshot, name) for name in ('CR0', 'CR4', 'EFER'))
    if cr0 & 0x80010000 != 0x80010000 or cr4 & 0x10a0 != 0x20 or efer & 0xc00 != 0xc00:
        raise ValueError('PAGING-QEMU: modo, proteccion de escritura o NX incorrectos')
    if data != MARKER + bytes(PAGE - len(MARKER)):
        raise ValueError('PAGING-QEMU: contenido fisico del alias distinto')

    tables = memory(base, 5 * PAGE, 'page-tables')
    expected = {
        0: (base + PAGE) | 7,
        512: (base + 2 * PAGE) | 3,
        513: (base + 3 * PAGE) | 7,
        3 * 512: (base + 4 * PAGE) | 7,
        4 * 512: (base + 5 * PAGE) | (1 << 63) | 5,
    }
    expected.update({1024 + index: (index << 21) | 0x83 for index in range(128)})
    for index, (entry,) in enumerate(struct.iter_unpack('<Q', tables)):
        wanted = expected.get(index, 0)
        if (entry & ~0x60 if wanted else entry) != wanted:
            raise ValueError(f'PAGING-QEMU: entrada {index} no coincide con el mapa esperado')
    return dict(ContextAccepted=True, PagingInstalled=True, OldCR3=f'0x{old_cr3:X}',
                ActiveCR3=f'0x{cr3:X}', TableFrames=5, TableBytes=5 * PAGE,
                DataFrames=1, FrameBytes=length, IdentityBytes=0x10000000,
                ConventionalBytes=sum(pages for kind, _, _, pages, _ in regions if kind == 7) * PAGE,
                Alias='0x40000000', AliasUser=True, AliasWritable=False, AliasExecutable=False,
                AliasReadback=True, WriteProtect=True, NXEnabled=True)
