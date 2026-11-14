"""Validate and run the first ULTRA-J binary profile on HOST."""
import argparse
import json
from pathlib import Path
import sys
from struct import Struct

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from host.diagnostics import Rejection


HEADER = Struct('<4sBBH')
STYLE = Struct('<BBBBII')
ARENA_BYTES = 256
CLASSES = {1: ('Window', 32), 2: ('Button', 16)}
OPEN, NEW, CLOSE, RETURN = 0x10, 0x20, 0x30, 0xff
CALL = 0x40
METHODS = {1: (1, b'show'), 2: (2, b'activate')}
MAX_CODE = 4096


def require(condition, code, offset, field):
    if not condition:
        raise Rejection(code, offset, field)


def check_header(data, magic, versions=(1,)):
    require(len(data) >= HEADER.size, 'TRUNCATED_HEADER', len(data), 'header')
    signature, version, flags, size = HEADER.unpack_from(data)
    require(signature == magic, 'MAGIC', 0, 'magic')
    require(version in versions, 'VERSION', 4, 'version')
    require(flags == 0, 'FLAGS', 5, 'flags')
    return size


def verify(data):
    size = check_header(data, b'UJBC', (1, 2))
    require(0 < size <= MAX_CODE and len(data) == HEADER.size + size,
            'CODE_SIZE', 6, 'code_size')
    offset = HEADER.size
    active, used = 0, 0
    instructions = []
    classes = []
    while offset < len(data):
        opcode = data[offset]
        if opcode == RETURN:
            require(active == 0, 'LIVE_REGION', offset, 'region')
            require(offset + 1 == len(data), 'AFTER_RETURN', offset + 1, 'opcode')
            return instructions
        require(opcode in (OPEN, NEW, CLOSE) or (opcode == CALL and data[4] == 2),
                'OPCODE', offset, 'opcode')
        width = 3 if opcode == CALL else 2
        require(offset + width <= len(data), 'MISSING_OPERAND', len(data), 'operand')
        operand = data[offset + 1]
        method = None
        if opcode == OPEN:
            require(active == 0 and operand != 0, 'REGION_OPEN', offset + 1, 'region')
            active, used = operand, 0
        elif opcode == NEW:
            require(active != 0, 'NO_REGION', offset, 'region')
            require(operand in CLASSES, 'CLASS', offset + 1, 'class')
            used += CLASSES[operand][1]
            require(used <= ARENA_BYTES, 'REGION_CAPACITY', offset, 'region')
            classes.append(operand)
        elif opcode == CALL:
            require(active != 0 and operand < len(classes), 'RECEIVER', offset + 1, 'receiver')
            method = data[offset + 2]
            require(method == METHODS[classes[operand]][0], 'METHOD', offset + 2, 'method')
        else:
            require(active != 0 and operand == active, 'REGION_CLOSE', offset + 1, 'region')
            active = 0
            classes.clear()
        instructions.append((opcode, operand, method))
        offset += width
    raise Rejection('MISSING_RETURN', offset, 'opcode')


def theme(data):
    count = check_header(data, b'UJTH')
    require(count == len(CLASSES) and len(data) == HEADER.size + count * STYLE.size,
            'STYLE_COUNT', 6, 'style_count')
    styles = {}
    for index, exp_class in enumerate(CLASSES):
        offset = HEADER.size + index * STYLE.size
        class_id, radius, padding, reserved, background, foreground = STYLE.unpack_from(data, offset)
        require(class_id == exp_class, 'STYLE_CLASS', offset, 'class')
        require(radius <= 32, 'STYLE_RADIUS', offset + 1, 'radius')
        require(padding <= 32, 'STYLE_PADDING', offset + 2, 'padding')
        require(reserved == 0, 'STYLE_RESERVED', offset + 3, 'reserved')
        require(background <= 0xffffff, 'STYLE_RGB', offset + 4, 'background')
        require(foreground <= 0xffffff, 'STYLE_RGB', offset + 8, 'foreground')
        styles[CLASSES[class_id][0]] = dict(Radius=radius, Padding=padding,
                                            Background=f'#{background:06X}', Foreground=f'#{foreground:06X}')
    return styles


def run(program, appearance):
    instructions = verify(program)
    styles = theme(appearance)
    arena = bytearray(ARENA_BYTES)
    used, peak, objects = 0, 0, 0
    allocations, releases, calls, slots = [], [], [], []
    for opcode, operand, method in instructions:
        if opcode == NEW:
            name, size = CLASSES[operand]
            end = used + size
            arena[used:end] = bytes(size)
            arena[used] = operand
            slots.append(used)
            allocations.append(dict(Class=name, Offset=used, Bytes=size))
            used = end
            peak = max(peak, used)
            objects += 1
        elif opcode == CALL:
            target = slots[operand]
            old = arena[target + 1]
            arena[target + 1] = 1
            calls.append(dict(Receiver=operand, Method=method, Before=old, After=1))
        elif opcode == CLOSE:
            releases.append(dict(Region=operand, Objects=objects, Bytes=used))
            used, objects = 0, 0
            slots.clear()
    return dict(Evidence='HOST', BytecodeBytes=len(program), ThemeBytes=len(appearance),
                ArenaBytes=len(arena), PeakObjectBytes=peak, LiveObjectBytes=used,
                Allocations=allocations, Releases=releases, Calls=calls, Styles=styles)


def read_bounded(path, maximum):
    with path.open('rb') as source:
        data = source.read(maximum + 1)
    require(len(data) <= maximum, 'FILE_SIZE', maximum, 'file')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('program', type=Path)
    parser.add_argument('theme', type=Path)
    args = parser.parse_args()
    try:
        report = run(read_bounded(args.program, HEADER.size + MAX_CODE),
                     read_bounded(args.theme, HEADER.size + len(CLASSES) * STYLE.size))
    except Rejection as error:
        print(json.dumps(error.report()), file=sys.stderr)
        return 1
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
