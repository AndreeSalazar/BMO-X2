"""Build the initial GA10x message-queue pages for GSP release 615.78.08."""

import argparse
import hashlib
import json
from pathlib import Path
import struct


PAGE = 4096
DMA_LIMIT = 1 << 52
MSG_COUNT = 63
QUEUE_BYTES = (1 + MSG_COUNT) * PAGE
COMMAND_OFFSET = PAGE
STATUS_OFFSET = COMMAND_OFFSET + QUEUE_BYTES
GSPMEM_PAGES = (STATUS_OFFSET + QUEUE_BYTES) // PAGE
ARGUMENT_BYTES = 184


def encode(rmargs_iova, gspmem_iovas):
    """Return one RMARGS page followed by GspMem pages in mapping order."""
    if not isinstance(gspmem_iovas, list) or len(gspmem_iovas) != GSPMEM_PAGES:
        raise ValueError(f'GspMem requiere {GSPMEM_PAGES} IOVA')
    addresses = [rmargs_iova, *gspmem_iovas]
    if any(type(address) is not int or not PAGE <= address < DMA_LIMIT or address % PAGE
           for address in addresses):
        raise ValueError('IOVA fuera de rango o desalineada')
    if len(set(addresses)) != len(addresses):
        raise ValueError('IOVA duplicada entre RMARGS, tabla y colas')

    image = bytearray(len(addresses) * PAGE)
    # GSP_ARGUMENTS_CACHED and its nested MESSAGE_QUEUE_INIT_ARGUMENTS.
    struct.pack_into('<4sH2xQ', image, 0, b'GSP ', ARGUMENT_BYTES, 2)
    struct.pack_into('<4Q6I', image, 16, 0, gspmem_iovas[0], COMMAND_OFFSET, STATUS_OFFSET,
                     24, PAGE, 16 * PAGE, 4, 12, GSPMEM_PAGES)
    struct.pack_into(f'<{GSPMEM_PAGES}Q', image, PAGE, *gspmem_iovas)
    # MSGQ v2 does not keep producer/consumer counters in the header.
    # The GSP initializes the status queue on its side of the channel.
    struct.pack_into('<2H4I', image, PAGE + COMMAND_OFFSET, 2, 0,
                     QUEUE_BYTES, PAGE, MSG_COUNT, PAGE)
    return bytes(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iovas', type=Path, help='JSON with rmargs_iova and gspmem_iovas')
    parser.add_argument('output', type=Path, help='New file, RMARGS page followed by GspMem pages')
    args = parser.parse_args()
    try:
        spec = json.loads(args.iovas.read_text(encoding='ascii'))
        if not isinstance(spec, dict) or set(spec) != {'rmargs_iova', 'gspmem_iovas'}:
            raise ValueError('Se requieren rmargs_iova y gspmem_iovas')
        image = encode(**spec)
        with args.output.open('xb') as stream:
            stream.write(image)
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP: {error}\n')
    print(json.dumps(dict(release='615.78.08', rmargs_iova=spec['rmargs_iova'],
                          gspmem_root_iova=spec['gspmem_iovas'][0], gspmem_pages=GSPMEM_PAGES,
                          bytes=len(image), sha256=hashlib.sha256(image).hexdigest()), indent=2))


if __name__ == '__main__':
    main()
