"""Compile the first Java-syntax ULTRA-J profile to UJBC."""
import argparse
import json
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from time import sleep

from runtime import CLASSES, CLOSE, HEADER, MAX_CODE, NEW, OPEN, RETURN
from runtime import Rejection, read_bounded, require, verify


MAX_SOURCE = 64 * 1024
TOKENS = re.compile(rb'(?P<trivia>\s+|//[^\r\n]*|/\*.*?\*/)|'
                    rb'(?P<token>[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+|[{}();=])|(?P<invalid>.)', re.S)
IDENTIFIER = re.compile(rb'[A-Za-z_$][A-Za-z0-9_$]*')
DECIMAL = re.compile(rb'[1-9][0-9]{0,2}')
CLASS_IDS = {name.encode('ascii'): number for number, (name, _) in CLASSES.items()}
RESERVED = frozenset(b'''
    abstract assert boolean break byte case catch char class const continue default do
    double else enum extends false final finally float for goto if implements import
    instanceof int interface long native new null package private protected public
    return short static strictfp super switch synchronized this throw throws transient
    true try void volatile while _ var yield record sealed permits Region Window Button
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
        self.advance()


def compile_source(data):
    require(len(data) <= MAX_SOURCE, 'SOURCE_SIZE', MAX_SOURCE, 'source')
    source = Source(data)
    source.take(b'class')
    source.identifier()
    source.take(b'{', b'void', b'run', b'(', b')', b'{')
    code = bytearray()
    locations = []
    while source.token == b'try':
        source.take(b'try', b'(', b'Region')
        source.identifier()
        source.take(b'=', b'new', b'Region', b'(')
        region_offset = source.offset
        require(DECIMAL.fullmatch(source.token) and int(source.token) <= 255,
                'SOURCE_REGION', region_offset, 'region')
        region = int(source.token)
        source.advance()
        source.take(b')', b')', b'{')
        code.extend((OPEN, region))
        locations.append(region_offset)
        while source.token == b'new':
            source.take(b'new')
            require(source.token in CLASS_IDS, 'SOURCE_CLASS', source.offset, 'class')
            code.extend((NEW, CLASS_IDS[source.token]))
            locations.append(source.offset)
            source.advance()
            source.take(b'(', b')', b';')
        locations.append(source.offset)
        source.take(b'}')
        code.extend((CLOSE, region))
    return_offset = source.offset
    source.take(b'return', b';', b'}', b'}', b'')
    code.append(RETURN)
    locations.append(return_offset)
    require(len(code) <= MAX_CODE, 'SOURCE_CODE_SIZE', return_offset, 'source')
    binary = HEADER.pack(b'UJBC', 1, 0, len(code)) + code
    try:
        verify(binary)
    except Rejection as error:
        source_offset = locations[(error.offset - HEADER.size) // 2]
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
            sleep(0.25)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
