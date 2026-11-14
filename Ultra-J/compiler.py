"""Compile the first Java-syntax ULTRA-J profile to UJBC."""
import argparse
import json
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from time import sleep

from runtime import CALL, CLASSES, CLOSE, HEADER, MAX_CODE, METHODS, NEW, OPEN, PRINT, RETURN
from runtime import Rejection, read_bounded, require, verify


MAX_SOURCE = 64 * 1024
WATCH_INTERVAL = 0.010
TOKENS = re.compile(rb'(?P<trivia>\s+|//[^\r\n]*|/\*.*?\*/)|'
                    rb'(?P<token>"[^"\r\n]*"|[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+|[{}();=.])|(?P<invalid>.)', re.S)
IDENTIFIER = re.compile(rb'[A-Za-z_$][A-Za-z0-9_$]*')
DECIMAL = re.compile(rb'[1-9][0-9]{0,2}')
CLASS_IDS = {name.encode('ascii'): number for number, (name, _) in CLASSES.items()}
RESERVED = frozenset(b'''
    abstract assert boolean break byte case catch char class const continue default do
    double else enum extends false final finally float for goto if implements import
    instanceof int interface long native new null package private protected public
    return short static strictfp super switch synchronized this throw throws transient
    true try void volatile while _ var yield record sealed permits Region Window Button Console
'''.split())


class Source:
    def __init__(self, data):
        tokens = ((m.group(), m.start()) for m in TOKENS.finditer(data) if m.lastgroup != 'trivia')
        self.tokens = iter(tokens)
        self.token, self.offset = b'', 0
        self.end = len(data)
        self.advance()

    def advance(self):
        self.token, self.offset = next(self.tokens, (b'', self.end))

    def take(self, *words):
        for word in words:
            require(self.token == word, 'SOURCE_EXPECTED', self.offset, word.decode('ascii'))
            self.advance()

    def identifier(self):
        require(IDENTIFIER.fullmatch(self.token) and self.token not in RESERVED,
                'SOURCE_IDENTIFIER', self.offset, 'identifier')
        name = self.token
        self.advance()
        return name


def region_value(source, parameter, argument):
    token = source.token
    if token == parameter:
        value = argument
    else:
        require(DECIMAL.fullmatch(token) and int(token) <= 255,
                'SOURCE_REGION', source.offset, 'region de 1 a 255')
        value = int(token)
    source.advance()
    return value


def compile_source(data, resolve_crate=None, crate_name=None, argument=None):
    require(len(data) <= MAX_SOURCE, 'SOURCE_SIZE', MAX_SOURCE, 'source')
    source = Source(data)
    source.take(b'class')
    class_offset = source.offset
    name = source.identifier()
    if crate_name is not None:
        require(name == crate_name, 'CRATE_CLASS', class_offset, crate_name.decode('ascii'))
    source.take(b'{')
    if crate_name is not None:
        source.take(b'static')
    source.take(b'void', b'run', b'(')
    parameter = None
    if crate_name is not None:
        signature_offset = source.offset
        if source.token == b'int':
            source.advance()
            parameter = source.identifier()
        require((parameter is None) == (argument is None), 'CRATE_ARITY',
                signature_offset, 'run(int)' if parameter is not None else 'run()')
    source.take(b')', b'{')
    code = bytearray()
    locations = {}
    version = 1
    while source.token != b'return':
        if source.token == b'Console':
            source.take(b'Console', b'.', b'println', b'(')
            text = source.token[1:-1]
            require(source.token.startswith(b'"') and source.token.endswith(b'"') and len(text) <= 255
                    and all(32 <= byte <= 126 and byte != 92 for byte in text),
                    'SOURCE_TEXT', source.offset, 'literal ASCII de hasta 255 bytes sin escapes')
            source.advance()
            source.take(b')', b';')
            code.extend((PRINT, len(text)))
            code.extend(text)
            version = 3
            continue
        if source.token != b'try':
            require(resolve_crate is not None, 'SOURCE_EXPECTED', source.offset, 'try o return')
            offset = source.offset
            name = source.identifier()
            source.take(b'.', b'run', b'(')
            value = None if source.token == b')' else region_value(source, parameter, argument)
            source.take(b')', b';')
            imported = resolve_crate(name, value, offset)
            code.extend(imported[HEADER.size:-1])
            version = max(version, imported[4])
            require(len(code) < MAX_CODE, 'SOURCE_CODE_SIZE', offset, 'source')
            continue
        source.take(b'try', b'(', b'Region')
        region_name = source.identifier()
        require(region_name != parameter, 'SOURCE_DUPLICATE', source.offset, 'region')
        source.take(b'=', b'new', b'Region', b'(')
        region_offset = source.offset
        region = region_value(source, parameter, argument)
        source.take(b')', b')', b'{')
        locations[len(code)] = region_offset
        code.extend((OPEN, region))
        bindings = {}
        slot = 0
        while source.token != b'}':
            offset = source.offset
            if source.token in bindings:
                receiver, class_id = bindings[source.identifier()]
                source.take(b'.')
                method, name = METHODS[class_id]
                source.take(name, b'(', b')', b';')
                code.extend((CALL, receiver, method))
                version = max(version, 2)
                continue
            declared = None
            if source.token in CLASS_IDS:
                declared = source.token
                source.advance()
                name_offset = source.offset
                name = source.identifier()
                require(name not in bindings and name not in (region_name, parameter),
                        'SOURCE_DUPLICATE', name_offset, 'receiver')
                source.take(b'=')
            source.take(b'new')
            require(source.token in CLASS_IDS and (declared is None or source.token == declared),
                    'SOURCE_CLASS', source.offset, 'class')
            class_id = CLASS_IDS[source.token]
            locations[len(code)] = source.offset
            code.extend((NEW, class_id))
            source.advance()
            source.take(b'(', b')', b';')
            if declared is not None:
                require(slot < 256, 'REGION_CAPACITY', offset, 'region')
                bindings[name] = (slot, class_id)
            slot += 1
        locations[len(code)] = source.offset
        source.take(b'}')
        code.extend((CLOSE, region))
    return_offset = source.offset
    source.take(b'return', b';', b'}', b'}', b'')
    code.append(RETURN)
    require(len(code) <= MAX_CODE, 'SOURCE_CODE_SIZE', return_offset, 'source')
    binary = HEADER.pack(b'UJBC', version, 0, len(code)) + code
    try:
        verify(binary)
    except Rejection as error:
        source_offset = locations.get(error.offset - HEADER.size, return_offset)
        raise Rejection(error.code, source_offset, error.field) from error
    return bytes(binary)


def publish(output, binary):
    temp = None
    try:
        with NamedTemporaryFile(dir=output.parent, delete=False) as file:
            temp = Path(file.name)
            file.write(binary)
        temp.replace(output)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve() or args.output.suffix.lower() != '.ujb':
        parser.error('La salida .ujb debe ser distinta del fuente')
    previous = None
    previous_error = None
    try:
        while True:
            try:
                data = read_bounded(args.source, MAX_SOURCE)
                if data != previous or not args.output.is_file():
                    binary = compile_source(data)
                    publish(args.output, binary)
                    previous = data
                    print(json.dumps(dict(Bytes=len(binary), Output=str(args.output))), flush=True)
                previous_error = None
                if not args.watch:
                    return 0
            except (OSError, Rejection) as error:
                report = error.report() if isinstance(error, Rejection) else dict(Error=str(error))
                if report != previous_error:
                    print(json.dumps(report), file=sys.stderr, flush=True)
                    previous_error = report
                if not args.watch:
                    return 1
            sleep(WATCH_INTERVAL)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
