"""Read-only census of PE32+ x64 exception metadata."""

from collections import Counter
import struct

from ..diagnostics import Rejection


FUNCTION = struct.Struct('<III')
MAX_FUNCTIONS = 1 << 18


def inventory_unwind(data, sections, directory, directory_offset):
    def locate(rva, size, source, field, *, executable=False):
        matches = []
        for section in sections:
            delta = rva - section['RVA']
            limit = min(section['VirtualBytes'] or section['FileBytes'], section['FileBytes'])
            if 0 <= delta and delta + size <= limit and (not executable or section['Executable']):
                matches.append((section['FileOffset'] + delta, limit - delta))
        if len(matches) != 1:
            raise Rejection('PE-UNWIND-INVENTORY-RVA', source, field)
        return matches[0]

    rva, size = directory['RVA'], directory['Bytes']
    if rva % 4 or not size or size % FUNCTION.size:
        raise Rejection('PE-UNWIND-INVENTORY-TABLE', directory_offset, 'DataDirectory.exceptions')
    count = size // FUNCTION.size
    if count > MAX_FUNCTIONS:
        raise Rejection('PE-UNWIND-INVENTORY-LIMIT', directory_offset, 'RUNTIME_FUNCTION',
                        actual=count, limit=MAX_FUNCTIONS)
    table, _ = locate(rva, size, directory_offset, 'DataDirectory.exceptions')
    versions, handlers = Counter(), Counter()
    exception_count = termination_count = chain_count = 0
    previous_end = 0
    for at in range(table, table + size, FUNCTION.size):
        begin, end, unwind = FUNCTION.unpack_from(data, at)
        if not previous_end <= begin < end or unwind % 4:
            raise Rejection('PE-UNWIND-INVENTORY-FUNCTION', at, 'RUNTIME_FUNCTION')
        locate(begin, end - begin, at, 'BeginAddress/EndAddress', executable=True)
        previous_end = end
        info, available = locate(unwind, 4, at + 8, 'UnwindData')
        version_flags, prolog, slots, _ = struct.unpack_from('<BBBB', data, info)
        version, flags = version_flags & 7, version_flags >> 3
        versions[version] += 1
        if version != 1:
            continue
        tail = 4 + ((slots + 1) & ~1) * 2
        tail_bytes = 12 if flags & 4 else 4 if flags & 3 else 0
        if (flags & ~7 or (flags & 4 and flags & 3) or prolog > end - begin
                or tail + tail_bytes > available):
            raise Rejection('PE-UNWIND-INVENTORY-INFO', info, 'UNWIND_INFO')
        if flags & 4:
            chain_count += 1
        elif flags & 3:
            handler, = struct.unpack_from('<I', data, info + tail)
            locate(handler, 1, info + tail, 'ExceptionHandler', executable=True)
            handlers[handler] += 1
            exception_count += bool(flags & 1)
            termination_count += bool(flags & 2)
    return dict(
        FunctionCount=count, Versions=dict(sorted(versions.items())),
        V1ExceptionHandlerCount=exception_count, V1TerminationHandlerCount=termination_count,
        V1ChainedCount=chain_count,
        V1Handlers=[dict(RVA=handler, FunctionCount=handlers[handler]) for handler in sorted(handlers)],
    )
