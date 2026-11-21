"""Reference encoding for the GA10x LIBOS 3 arguments in 615.78.08."""

import struct

from .gsp_args import DMA_LIMIT, PAGE


# Bare-metal release defaults from NVIDIA's log setup and registry.
LOGS = (
    (b'LOGINIT', 16),
    (b'LOGINTR', 16),
    (b'LOGRM', 16),
    (b'LOGMNOC', 16),
    (b'LOGDBG', 16),
    (b'LOGROOT', 1),
    (b'LOGRMON', 1),
    (b'LOGKRNL', 16),
)
LIBOS_PAGES = 1 + sum(pages for _, pages in LOGS)


def encode(libos_iova, rmargs_iova):
    """Return the descriptor page followed by the initialized log buffers."""
    for address in (libos_iova, rmargs_iova):
        if type(address) is not int or not PAGE <= address < DMA_LIMIT or address % PAGE:
            raise ValueError('IOVA LIBOS desalineada o fuera de rango')
    end = libos_iova + LIBOS_PAGES * PAGE
    if end > DMA_LIMIT or libos_iova <= rmargs_iova < end:
        raise ValueError('RMARGS se solapa con LIBOS o la reserva excede el limite DMA')

    image = bytearray(LIBOS_PAGES * PAGE)
    offset = PAGE
    for index, (name, pages) in enumerate(LOGS):
        address = libos_iova + offset
        size = pages * PAGE
        struct.pack_into('<QQQBB6x', image, index * 32, int.from_bytes(name, 'big'), address, size, 1, 1)
        struct.pack_into('<Q', image, offset + 8, address)
        offset += size
    struct.pack_into('<QQQBB6x', image, len(LOGS) * 32, int.from_bytes(b'RMARGS', 'big'), rmargs_iova, PAGE, 1, 1)
    return bytes(image)
