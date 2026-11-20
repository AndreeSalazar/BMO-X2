"""Read the Ring 3 benchmark and account for BMO-X2 boot reservations."""
from math import ceil
from statistics import median
import struct


PAGE = 4096
FRAME_MASK = 0x000ffffffffff000
# UJBC v2: open region 1, create Window and Button, invoke both, close, return.
BENCHMARK_ACTION = bytes.fromhex('554a424302000f00 1001 2001 2002 400001 400102 3001 ff')


def read_benchmark(memory, context):
    record = struct.Struct('<8sQQ62Q')
    magic, batches, actions, *ticks = record.unpack(
        memory(context + 0x1d108, record.size, 'ultra-j-benchmark'))
    if (magic, batches, actions) != (b'UJBM0001', 31, 2048) or min(ticks) == 0:
        raise ValueError('Registro de comparacion ULTRA-J/Rust incompleto')

    def summarize(samples):
        ordered = sorted(samples)
        return dict(MedianTicksPerAction=round(median(ordered) / actions, 3),
                    P95TicksPerAction=round(ordered[ceil(batches * .95) - 1] / actions, 3),
                    BatchTicks=samples)

    return dict(Unit='QEMU guest TSC ticks', BatchesPerAction=batches, ActionsPerBatch=actions,
                BothActionsReturnedAndScrubbed=True, UJBC=summarize(ticks[::2]),
                RustNoStd=summarize(ticks[1::2]))


def user_frames(memory, context, phase):
    page = memory(context + 0x17000, PAGE, f'ultra-j-pages-{phase}')
    return {entry & FRAME_MASK for (entry,) in struct.iter_unpack('<Q', page) if entry & 5 == 5}


def boot_reservations(memory, context, code, cr3, framebuffer_bytes):
    fields = memory(context, 0xd0, 'ultra-j-reservations')
    map_bytes, map_stride = (struct.unpack_from('<Q', fields, offset)[0] for offset in (0x50, 0x60))
    if not 40 <= map_stride <= map_bytes <= 65536 or map_bytes % map_stride:
        raise ValueError('Mapa UEFI del escritorio invalido')
    snapshot = memory(context + 0x1000, map_bytes, 'ultra-j-uefi-map')
    regions = [struct.unpack_from('<I4xQQQ', snapshot, offset)
               for offset in range(0, map_bytes, map_stride)]
    stage, _, dma, dma_pages, stage_pages = struct.unpack_from('<5Q', fields, 0xa8)
    ranges = dict(Context=(context, 32, 2), BootPayload=(code, 1, 1),
                  SbefStaging=(stage, stage_pages, 2), XhciDma=(dma, dma_pages, 2))
    occupied = set()
    for name, (base, pages, kind) in ranges.items():
        if name == 'XhciDma' and pages == 0:
            continue
        if not (base and base % PAGE == 0 and 1 <= pages <= 32):
            raise ValueError(f'Reserva de arranque invalida: {name}')
        frames = {base + n * PAGE for n in range(pages)}
        if frames & occupied or not all(any(
                mem_kind == kind and start <= frame < start + count * PAGE
                for mem_kind, start, _, count in regions) for frame in frames):
            raise ValueError(f'Reserva fuera del mapa UEFI o duplicada: {name}')
        occupied.update(frames)

    tables = set()
    pending = [(cr3 & FRAME_MASK, 4)]
    while pending:
        frame, level = pending.pop()
        if frame in tables:
            continue
        if not context <= frame < context + 32 * PAGE:
            raise ValueError('Tabla activa fuera de la reserva de contexto')
        tables.add(frame)
        if level > 1:
            table = memory(frame, PAGE, f'ultra-j-table-{frame - context:x}')
            pending.extend((entry & FRAME_MASK, level - 1)
                           for (entry,) in struct.iter_unpack('<Q', table)
                           if entry & 1 and (level == 4 or not entry & 0x80))

    return dict(**{name + 'Bytes': pages * PAGE for name, (_, pages, _) in ranges.items()},
                KnownBootBytes=len(occupied) * PAGE, ActivePageTableBytes=len(tables) * PAGE,
                FramebufferVisibleBytes=framebuffer_bytes)
